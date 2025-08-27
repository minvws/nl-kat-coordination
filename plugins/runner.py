import datetime
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
        self.override_entrypoint = override_entrypoint
        self.adapter = adapter

    def run(self, plugin_id: str, target: str | None, output: str = "file"):
        use_stdout = str(output) == "-"

        try:
            IPAddress(target)
            is_ip = True
        except (AddrFormatError, ValueError):
            is_ip = False

        plugin = Plugin.objects.get(plugin_id=plugin_id)
        client = docker.from_env()

        # Temporary user with limited access rights
        plugin_user = KATUser(full_name=plugin_id, email=f"{uuid.uuid4()}@openkat.nl")
        plugin_user.set_unusable_password()
        plugin_user.save()
        plugin_user.user_permissions.add(Permission.objects.get(codename="view_file"))
        plugin_user.user_permissions.add(Permission.objects.get(codename="add_file"))

        token = AuthToken(
            user=plugin_user,
            name=plugin_id,
            expiry=datetime.datetime.now(timezone.utc) + timedelta(minutes=settings.PLUGIN_TIMEOUT),
        )

        # TODO: to get the original entrypoint run:
        #     original_entrypoint = client.images.get(plugin.oci_image).attrs["Config"]["Entrypoint"]
        #   (Perhaps we need this later on.)

        callback_kwargs = (
            {
                "entrypoint": self.override_entrypoint,
                "environment": {
                    "PLUGIN_ID": plugin.plugin_id,
                    "OPENKAT_TOKEN": token.generate_new_token(),
                    "OPENKAT_API": f"{settings.OPENKAT_HOST}/api/v1",  # TODO: generate
                },
                "network": settings.DOCKER_NETWORK,
                "volumes": [f"{self.adapter}:{self.override_entrypoint}"],
            }
            if not use_stdout
            else {
                "entrypoint": [],
                "environment": {
                    "PLUGIN_ID": plugin.plugin_id,
                    "OPENKAT_TOKEN": token.generate_new_token(),
                    "OPENKAT_API": f"{settings.OPENKAT_HOST}/api/v1",
                },
            }
        )
        token.save()

        args = plugin.oci_arguments

        if target is not None:
            # TODO: add nameserver through configuration later
            format_map = {"nameserver": "1.1.1.1", "ip_address|hostname": target, "file": target}

            if is_ip:
                format_map["ip_address"] = target
            else:
                format_map["hostname"] = target

            args = [arg.format_map(format_map) for arg in plugin.oci_arguments]

        logs = client.containers.run(
            image=plugin.oci_image,
            name=f"{plugin.plugin_id}_{datetime.datetime.now(timezone.utc).timestamp()}",
            command=args,
            stdout=use_stdout,
            stderr=True,
            remove=True,
            **callback_kwargs,
        )

        token.delete()
        plugin_user.delete()

        return logs
