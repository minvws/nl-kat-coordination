import datetime
import shlex
import signal
import uuid
from datetime import timedelta
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
        override_entrypoint: str = "/bin/runner",
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
        parallelism: int | None = None,  # TODO: fix
    ) -> str:
        use_stdout = str(output) == "-"
        plugin = Plugin.objects.get(plugin_id=plugin_id)
        environment = {"PLUGIN_ID": plugin.plugin_id, "OPENKAT_API": f"{settings.OPENKAT_HOST}/api/v1"}
        tmp_file = None

        if isinstance(target, str):
            if not plugin.types_in_arguments():
                tmp_file = File.objects.create(file=TemporaryContent(target))

            command = self.create_command(plugin.oci_arguments, target)
        elif target is None:
            command = plugin.oci_arguments
        elif isinstance(target, list):
            if plugin.types_in_arguments() or any("{file}" in arg for arg in plugin.oci_arguments):
                # This plugin expects one target object at a time.

                if len(target) == 1:
                    return self.run(plugin_id, target[0], output, task_id, keep, cli)

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
            else:
                tmp_file = File.objects.create(file=TemporaryContent("\n".join(target)))
                command = plugin.oci_arguments
        else:
            raise ValueError(f"Unsupported target type: {type(target)}")

        if tmp_file:
            environment["IN_FILE"] = str(tmp_file.id)
        if use_stdout:
            environment["UPLOAD_URL"] = "/dev/null"
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

        client = docker.from_env()

        container = client.containers.run(
            image=plugin.oci_image,
            name=f"{plugin.plugin_id}_{datetime.datetime.now(datetime.UTC).timestamp()}",
            command=command,
            stdout=use_stdout,
            stderr=True,
            network=settings.DOCKER_NETWORK,
            entrypoint=self.entrypoint,
            volumes=[f"{self.adapter}:{self.entrypoint}"],
            environment=environment,
            detach=True,
        )

        # Add signal handler to kill the container as well (for cancelling tasks)
        old_handle = signal.getsignal(signal.SIGTERM)

        def handle(sig_num, stack_frame):
            container.kill(sig_num)
            token.delete()
            plugin_user.delete()

            if tmp_file:
                tmp_file.delete()

            old_handle(sig_num, stack_frame)

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
            out = container.logs(stdout=False, stderr=True)

        if not keep:
            container.remove(force=True)

        token.delete()
        plugin_user.delete()

        if tmp_file:
            tmp_file.delete()

        if exit_status != 0:
            raise ContainerError(container, exit_status, command, container.image, out)

        signal.signal(signal.SIGTERM, old_handle)

        if out is None:
            return ""

        return b"".join(out).decode()

    def get_cli(self, command: list[str], environment: dict[str, str], keep: bool, plugin: Plugin) -> str:
        environment["OPENKAT_TOKEN"] = "$OPENKAT_TOKEN"  # We assume the user has set its own token if needed
        rm = "--rm" if not keep else ""
        envs = "-e " + " -e ".join([f"{k}={v}" for k, v in environment.items()]) if environment else ""
        network = f"--network {settings.DOCKER_NETWORK}"
        cmd = shlex.join(command)
        vol = f"-v {self.adapter}:{self.entrypoint}"

        return f"docker run {rm} {vol} --entrypoint {self.entrypoint} {envs} {network} {plugin.oci_image} {cmd}"

    @staticmethod
    def create_token(plugin_id: str) -> tuple[User, AuthToken]:
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
            expiry=datetime.datetime.now(datetime.UTC) + timedelta(minutes=settings.PLUGIN_TIMEOUT),
        )

        return plugin_user, token

    @staticmethod
    def create_command(args: list[str], target: str):
        format_map = {"{file}": target}

        for ip_key in ["{ipaddress}", "{ipaddressv4}", "{ipaddressv6}"]:
            format_map["{hostname|" + ip_key + "}"] = target
            format_map["{" + ip_key + "|hostname"] = target

            format_map[ip_key] = target

        format_map["{hostname}"] = target

        new_args = []

        for arg in args:
            for key, value in format_map.items():
                arg = arg.replace(key, value)

            new_args.append(arg)

        return new_args
