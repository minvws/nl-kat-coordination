import datetime
import shlex
import signal
import uuid
from datetime import UTC, timedelta
from pathlib import Path

import docker
from django.conf import settings
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from docker.errors import ContainerError

from files.models import File, TemporaryContent
from openkat.models import AuthToken, User
from plugins.models import Plugin


class PluginRunner:
    def __init__(
        self,
        override_entrypoint: str = "/bin/runner",  # Path to the entrypoint binary inside the container.
        # Path to the entrypoint binary on the host system, which will be mounted into the container.
        adapter: Path = Path(settings.HOST_MOUNT_DIR) / "plugins" / "plugins" / "entrypoint" / "main",
    ):
        self.entrypoint = override_entrypoint
        self.adapter = adapter

    def run(
        self,
        plugin_id: str,
        target: str | list[str] | None,
        output: str = "file",
        task_id: uuid.UUID | None = None,
        keep: bool = False,
        cli: bool = False,
        parallelism: int | None = None,  # TODO: auto-parallelism
    ) -> str:
        """
        Execute a plugin with different execution modes based on target type and plugin configuration.

        MODE 1 - Direct Argument (has placeholders, single target):
            - target: "example.com"
            - oci_arguments: ["tool", "{hostname}"]
            - Result: Runs as: tool example.com
            - No temporary file created

        MODE 2 - Standalone (no target):
            - target: None
            - oci_arguments: ["tool", "--fetch-url", "..."]
            - Result: Runs command as-is, no target substitution
            - Plugin fetches its own data

        MODE 3 - Sequential (has placeholders, list of targets):
            - target: ["example.com", "test.org"]
            - oci_arguments: ["tool", "{hostname}"]
            - Result: Runs tool example.com, then tool test.org (sequentially)
            - Each target runs in a separate container
            - Logs are concatenated

        MODE 4 - Bulk stdin (NO placeholders, single or list of targets):
            - target: "example.com" OR ["example.com", "test.org"]
            - oci_arguments: ["xargs", "-I", "%", "tool", "%"]
            - Result: Creates temp file with target(s) (newline-separated if list)
            - Sets IN_FILE environment variable
            - Entrypoint pipes file to plugin's stdin
            - Often uses xargs for parallel processing
            - Note: Single string target is converted to single-item list

        MODE 5 - File Processing (has {file} placeholder):
            - target: "<file_id>"
            - oci_arguments: ["tool", "{file}"]
            - Result: Replaces {file} with file_id, entrypoint fetches file
            - Alternative: Static file reference using {file/<id>} notation
              * oci_arguments: ["tool", "{file/123}"]
              * No target needed - file ID is embedded in the argument
              * Useful for creating plugins that always process specific files
              * Can be set via file list "Add to plugin" button

        CRITICAL: When oci_arguments has NO bracketed placeholders ({...}),
        data is passed via stdin through the entrypoint adapter, not as arguments.
        Single string targets are automatically converted to single-item lists
        to enable consistent stdin processing (MODE 4).

        Args:
            plugin_id: Unique identifier of the plugin to run
            target: The target(s) to process. Can be:
                - str: Single target (hostname, IP, file_id, etc.)
                - list[str]: Multiple targets
                - None: No target (plugin fetches own data)
            output: Where to send results:
                - "file": Upload to OpenKAT API (default)
                - "-": Output to stdout (for CLI usage)
            task_id: Optional task UUID to associate uploaded files with
            keep: If True, don't remove container after execution (for debugging)
            cli: If True, return the docker command instead of running it
            parallelism: Intended for parallel execution of list targets (currently disabled)

        Returns:
            Plugin output as string (stdout if output="-", otherwise container logs)

        Raises:
            ContainerError: If the plugin exits with non-zero status
            ValueError: If target type is not supported
        """
        use_stdout = str(output) == "-"
        plugin = Plugin.objects.get(plugin_id=plugin_id)
        environment = {"PLUGIN_ID": plugin.plugin_id, "OPENKAT_API": f"{settings.OPENKAT_HOST}/api/v1"}
        tmp_file = None
        has_placeholder = plugin.types_in_arguments() or any("{file}" in arg for arg in plugin.oci_arguments)

        # MODE 2
        command = plugin.oci_arguments

        if isinstance(target, str):
            # MODE 1
            if has_placeholder:
                command = self.create_command(plugin.oci_arguments, target)
            else:
                # This merges old MODE 2 into MODE 4
                target = [target]

        # MODE 3 & 4: List of targets
        if isinstance(target, list):
            # MODE 3: Has placeholders = sequential execution mode
            if has_placeholder:
                # TODO: auto-parallelism has hit an edge case, so it has been now turned off until the go binary
                #  supports handling auto-parallelism:
                #  parallelism = settings.AUTO_PARALLELISM if parallelism is None else parallelism

                logs = []
                for t in target:  # Run the targets sequentially
                    try:
                        logs.append(self.run(plugin_id, t, output, task_id, keep, cli))
                    except ContainerError:
                        logs.append(f"Failed to process target: {t}")

                return "\n".join(logs)  # Return the output merged

            # MODE 4: NO placeholders = bulk stdin mode
            else:
                tmp_file = File.objects.create(file=TemporaryContent("\n".join(target)))

        if not isinstance(target, (str, list, type(None))):
            raise ValueError(f"Unsupported target type: {type(target)}")

        # Set IN_FILE for stdin modes (entrypoint reads this file and pipes to plugin)
        if tmp_file:
            environment["IN_FILE"] = str(tmp_file.pk)

        # Configure where plugin output should go
        if use_stdout:
            environment["UPLOAD_URL"] = "/dev/null"  # CLI mode: don't upload
        elif task_id:
            environment["UPLOAD_URL"] = f"{settings.OPENKAT_HOST}/api/v1/file/?task_id={task_id}"
        else:
            environment["UPLOAD_URL"] = f"{settings.OPENKAT_HOST}/api/v1/file/"

        if cli:
            return self.get_cli(command, environment, keep, plugin)

        # Temporary user with limited access rights
        plugin_user, token = self.create_token(plugin_id)
        environment["OPENKAT_TOKEN"] = token.generate_new_token()
        token.save()

        # Add signal handler to kill the container as well (for cancelling tasks)
        original_handler = signal.getsignal(signal.SIGTERM)
        client = docker.from_env()
        container = client.containers.run(
            image=plugin.oci_image,
            name=f"{plugin.plugin_id}_{datetime.datetime.now(UTC).timestamp()}",
            command=command,
            stdout=use_stdout,
            stderr=True,
            network=settings.DOCKER_NETWORK,
            entrypoint=self.entrypoint,
            volumes=[f"{self.adapter}:{self.entrypoint}"],
            environment=environment,
            detach=True,
        )

        def handle(signalnum, stack_frame):
            container.kill(signalnum)
            container.remove(force=True)

            token.delete()
            plugin_user.delete()

            if tmp_file:
                tmp_file.delete()

            if callable(original_handler):
                original_handler(signalnum, stack_frame)
            elif original_handler == signal.SIG_DFL:
                # Call the default signal handler
                signal.default_int_handler(signalnum, stack_frame)
            elif original_handler == signal.SIG_IGN:
                # Signal was being ignored
                pass

        signal.signal(signal.SIGTERM, handle)

        # TODO: consider asynchronous handling. We only need to figure out how to handle dropping authorization rights
        #   after the container has gone.

        # Below is a copy of the implementation of container.run() after the check if detach equals True.
        logging_driver = container.attrs["HostConfig"]["LogConfig"]["Type"]

        out = None
        if logging_driver == "json-file" or logging_driver == "journald":
            out = container.logs(stdout=use_stdout, stderr=True, stream=True, follow=True)

        exit_status = container.wait()["StatusCode"]
        if exit_status != 0:
            stderr_out = container.logs(stdout=False, stderr=True)

        if not keep:
            container.remove(force=True)

        token.delete()
        plugin_user.delete()

        if tmp_file:
            tmp_file.delete()

        if exit_status != 0:
            raise ContainerError(container, exit_status, command, str(container.image), stderr_out.decode())

        signal.signal(signal.SIGTERM, original_handler)

        if out is None:
            return ""

        return b"".join(out).decode()

    def get_cli(self, command: list[str], environment: dict[str, str], keep: bool, plugin: Plugin) -> str:
        """
        Generate the equivalent docker run command for manual execution.

        This is useful for debugging plugins locally. The user must set their own
        OPENKAT_TOKEN environment variable before running the command.

        Args:
            command: The plugin command to execute
            environment: Environment variables to pass to the container
            keep: Whether to keep the container after execution
            plugin: The plugin being executed

        Returns:
            A complete docker run command as a string
        """

        environment["OPENKAT_TOKEN"] = "$OPENKAT_TOKEN"  # We assume the user has set its own token if needed
        rm = "--rm" if not keep else ""
        envs = "-e " + " -e ".join([f"{k}={v}" for k, v in environment.items()]) if environment else ""
        network = f"--network {settings.DOCKER_NETWORK}"
        cmd = shlex.join(command)
        vol = f"-v {self.adapter}:{self.entrypoint}"

        return f"docker run {rm} {vol} --entrypoint {self.entrypoint} {envs} {network} {plugin.oci_image} {cmd}"

    @staticmethod
    def create_token(plugin_id: str) -> tuple[User, AuthToken]:
        """
        Create a temporary user and auth token for the plugin to use.

        The plugin gets limited permissions:
        - Can view and add files (for uploading results)
        - Can view/add/change/delete all object types (Network, Hostname, IPAddress, etc.)

        The token expires after PLUGIN_TIMEOUT minutes and is deleted after the plugin completes.

        Args:
            plugin_id: Identifier of the plugin (used as the user's full_name)

        Returns:
            Tuple of (temporary_user, auth_token)
        """

        plugin_user = User(full_name=plugin_id, email=f"{uuid.uuid4()}@openkat.nl")
        plugin_user.set_unusable_password()
        plugin_user.save()

        plugin_user.user_permissions.add(Permission.objects.get(codename="view_file"))
        plugin_user.user_permissions.add(Permission.objects.get(codename="add_file"))

        content_types = ContentType.objects.filter(app_label="objects")
        permissions = Permission.objects.filter(content_type__in=content_types)
        plugin_user.user_permissions.add(*permissions)

        token = AuthToken(
            user=plugin_user,
            name=plugin_id,
            expiry=datetime.datetime.now(UTC) + timedelta(minutes=settings.PLUGIN_TIMEOUT),
        )

        return plugin_user, token

    @staticmethod
    def create_command(args: list[str], target: str) -> list[str]:
        """
        Replace bracketed placeholders in oci_arguments with the actual target value.

        This enables MODE 1 (Direct Argument) execution where targets are passed
        as command-line arguments to the plugin.

        Supported placeholders:
        - {file}: File ID from previous plugin output (replaced with target value)
        - {file/<id>}: Static file reference (e.g., {file/123} stays as-is)
        - {hostname}: Hostname target
        - {ipaddress}: IP address target

        Note: Static file references like {file/123} are NOT replaced by this function
        and remain in the arguments as-is. The entrypoint adapter will recognize and
        fetch these files by their embedded IDs.

        Example:
            args: ["tool", "--target", "{hostname}"]
            target: "example.com"
            Result: ["tool", "--target", "example.com"]

        Example with static file reference:
            args: ["tool", "--config", "{file/123}"]
            target: "example.com"
            Result: ["tool", "--config", "{file/123}"]  # {file/123} preserved

        Args:
            args: The oci_arguments list from the plugin configuration
            target: The target value to substitute into placeholders

        Returns:
            New list with placeholders replaced by target value
        """

        format_map = {"{file}": target}
        format_map["{ipaddress}"] = target
        format_map["{hostname}"] = target
        format_map["{mail_server}"] = target

        new_args = []

        for arg in args:
            for key, value in format_map.items():
                arg = arg.replace(key, value)

            new_args.append(arg)

        return new_args
