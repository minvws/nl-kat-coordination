import datetime
import shlex
import uuid
from datetime import timedelta, timezone
from pathlib import Path

import docker
from django.conf import settings
from django.contrib.auth.models import Permission
from netaddr import AddrFormatError, IPAddress

from account.models import AuthToken, KATUser
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
    ) -> str:
        use_stdout = str(output) == "-"

        try:
            IPAddress(target)
            is_ip = True
        except (AddrFormatError, ValueError, TypeError, AttributeError):
            is_ip = False

        plugin = Plugin.objects.get(plugin_id=plugin_id)
        client = docker.from_env()

        # Temporary user with limited access rights
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

        # TODO: to get the original entrypoint run:
        #     original_entrypoint = client.images.get(plugin.oci_image).attrs["Config"]["Entrypoint"]
        #   (Perhaps we need this later on.)
        environment = {
            "PLUGIN_ID": plugin.plugin_id,
            "OPENKAT_TOKEN": token.generate_new_token(),
            "OPENKAT_API": f"{settings.OPENKAT_HOST}/api/v1",  # TODO: generate
        }

        if use_stdout:
            environment["UPLOAD_URL"] = "/dev/null"
        elif task_id:
            environment["UPLOAD_URL"] = f"http://openkat:8000/api/v1/file/?task_id={task_id}"

        token.save()

        args = plugin.oci_arguments

        if isinstance(target, str):
            # TODO: add nameserver through configuration later
            format_map = {"nameserver": "1.1.1.1", "file": target}

            for ip_key in ["ipaddress", "ipaddressv4", "ipaddressv6"]:
                format_map[f"hostname|{ip_key}"] = target
                format_map[f"{ip_key}|hostname"] = target

            if is_ip:
                format_map["ipaddress"] = target
                format_map["ipaddressv4"] = target
                format_map["ipaddressv6"] = target
            else:
                format_map["hostname"] = target

            new_args = []

            for arg in args:
                try:
                    new_args.append(arg.format_map(format_map))
                except KeyError:
                    new_args.append(arg)
        else:
            new_args = args

        if cli:
            rm = "--rm" if not keep else ""
            envs = "-e " + " -e ".join([f"{k}={v}" for k, v in environment.items()]) if environment else ""
            network = f"--network {settings.DOCKER_NETWORK}"
            cmd = shlex.join(new_args)
            vol = f"-v {self.adapter}:{self.entrypoint}"

            return f"docker run {rm} {vol} --entrypoint {self.entrypoint} {envs} {network} {plugin.oci_image} {cmd}"

        logs = client.containers.run(
            image=plugin.oci_image,
            name=f"{plugin.plugin_id}_{datetime.datetime.now(timezone.utc).timestamp()}",
            command=new_args,
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

        return logs.decode()
