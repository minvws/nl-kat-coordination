import datetime
import shlex
import uuid
from datetime import timedelta, timezone
from pathlib import Path

import docker
from django.conf import settings
from django.contrib.auth.models import Permission

from account.models import AuthToken, KATUser
from files.models import File, TemporaryContent
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
        parallelism: int | None = None,
    ) -> str:
        use_stdout = str(output) == "-"
        plugin = Plugin.objects.get(plugin_id=plugin_id)

        # Temporary user with limited access rights
        environment = {
            "PLUGIN_ID": plugin.plugin_id,
            "OPENKAT_API": f"{settings.OPENKAT_HOST}/api/v1",  # TODO: generate?
        }

        if use_stdout:
            environment["UPLOAD_URL"] = "/dev/null"
        elif task_id:
            environment["UPLOAD_URL"] = f"http://openkat:8000/api/v1/file/?task_id={task_id}"

        tmp_file = None

        if isinstance(target, str):
            command = self.create_command(plugin.oci_arguments, target)
        elif target is None:
            command = plugin.oci_arguments
        elif isinstance(target, list):
            if plugin.types_in_arguments() or any("{file}" in arg for arg in plugin.oci_arguments):
                # This plugin expects one target object at a time, so we automatically parallelize with xargs if needed.
                if len(target) == 1:
                    return self.run(plugin_id, target[0], output, task_id, keep, cli)

                parallelism = settings.AUTO_PARALLELISM if parallelism is None else parallelism
                if parallelism == 0:
                    logs = []
                    for t in target:
                        logs.append(self.run(plugin_id, t, output, task_id, keep, cli))

                    return "".join(logs)

                tmp_file = File.objects.create(file=TemporaryContent("\n".join(target)))
                environment["IN_FILE"] = str(tmp_file.id)
                command = ["xargs", "-P", str(parallelism), "-I", "%"] + self.create_command(plugin.oci_arguments, "%")
            else:
                tmp_file = File.objects.create(file=TemporaryContent("\n".join(target)))
                environment["IN_FILE"] = str(tmp_file.id)

                command = plugin.oci_arguments
        else:
            raise ValueError(f"Unsuported target type: {type(target)}")

        if cli:
            return self.get_cli(command, environment, keep, plugin)

        plugin_user, token = self.create_token(plugin_id)
        environment["OPENKAT_TOKEN"] = token.generate_new_token()
        token.save()

        client = docker.from_env()
        logs = client.containers.run(
            image=plugin.oci_image,
            name=f"{plugin.plugin_id}_{datetime.datetime.now(timezone.utc).timestamp()}",
            command=command,
            stdout=use_stdout,
            stderr=True,
            remove=not keep,
            network=settings.DOCKER_NETWORK,
            entrypoint=self.entrypoint,
            volumes=[f"{self.adapter}:{self.entrypoint}"],
            environment=environment,
        )
        # TODO: consider asynchronous handling. We only need to figure out how to handle dropping authorization rights
        #   after the container has gone.

        token.delete()
        plugin_user.delete()

        if tmp_file:
            tmp_file.delete()

        return logs.decode()

    def get_cli(self, command: list[str], environment: dict[str, str], keep: bool, plugin: Plugin) -> str:
        environment["OPENKAT_TOKEN"] = "$OPENKAT_TOKEN"  # We assume the user has set its own token if needed
        rm = "--rm" if not keep else ""
        envs = "-e " + " -e ".join([f"{k}={v}" for k, v in environment.items()]) if environment else ""
        network = f"--network {settings.DOCKER_NETWORK}"
        cmd = shlex.join(command)
        vol = f"-v {self.adapter}:{self.entrypoint}"
        return f"docker run {rm} {vol} --entrypoint {self.entrypoint} {envs} {network} {plugin.oci_image} {cmd}"

    def create_token(self, plugin_id: str) -> tuple[KATUser, AuthToken]:
        plugin_user = KATUser(full_name=plugin_id, email=f"{uuid.uuid4()}@openkat.nl")
        plugin_user.set_unusable_password()
        plugin_user.save()

        plugin_user.user_permissions.add(Permission.objects.get(codename="view_file"))
        plugin_user.user_permissions.add(Permission.objects.get(codename="add_file"))
        plugin_user.user_permissions.add(Permission.objects.get(codename="add_ooi"))

        token = AuthToken(
            user=plugin_user,
            name=plugin_id,
            expiry=datetime.datetime.now(timezone.utc) + timedelta(minutes=settings.PLUGIN_TIMEOUT),
        )

        return plugin_user, token

    def create_command(self, args: list[str], target: str):
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
