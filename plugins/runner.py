import datetime
from datetime import timezone
from pathlib import Path

import docker
from django.conf import settings
from netaddr import AddrFormatError, IPAddress

from plugins.models import Plugin


class PluginRunner:
    def __init__(
        self, override_entrypoint: str = "/bin/runner", plugins_dir: Path = settings.BASE_DIR / "plugins" / "plugins"
    ):
        self.override_entrypoint = override_entrypoint
        self.plugins_dir = plugins_dir

    def run(self, plugin_id: str, target: str, output: str = "file"):
        use_stdout = str(output) == "-"

        try:
            IPAddress(target)
            is_ip = True
        except AddrFormatError:
            is_ip = False

        plugin = Plugin.objects.get(plugin_id=plugin_id)

        client = docker.from_env()

        # TODO: to get the original entrypoint run:
        #     original_entrypoint = client.images.get(plugin.oci_image).attrs["Config"]["Entrypoint"]
        #   (Perhaps we need this later on.)

        callback_kwargs = (
            {
                "entrypoint": self.override_entrypoint,
                "environment": {"PLUGIN_ID": plugin.plugin_id},
                "network": settings.DOCKER_NETWORK,
                "volumes": [f'{(self.plugins_dir / "entrypoint" / "main").absolute()}:{self.override_entrypoint}'],
            }
            if not use_stdout
            else {"entrypoint": []}
        )

        # TODO: add nameserver through configuration later
        format_map = {"nameserver": "1.1.1.1", "ip_address|hostname": target}

        if is_ip:
            format_map["ip_address"] = target
        else:
            format_map["hostname"] = target

        return client.containers.run(
            image=plugin.oci_image,
            name=f"{plugin.plugin_id}_{datetime.datetime.now(timezone.utc).timestamp()}",
            command=[arg.format_map(format_map) for arg in plugin.oci_arguments],
            stdout=use_stdout,
            stderr=True,
            remove=True,
            **callback_kwargs,
        )
