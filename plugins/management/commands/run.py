import datetime
from datetime import timezone
from pathlib import Path

import docker
from django.conf import settings
from django.core.management.base import BaseCommand
from netaddr import AddrFormatError, IPAddress

from plugins.models import Plugin


class PluginRunner:
    def __init__(
        self, override_entrypoint: str = "/bin/runner", plugins_dir: Path = settings.BASE_DIR / "plugins" / "plugins"
    ):
        self.override_entrypoint = override_entrypoint
        self.plugins_dir = plugins_dir

    def run(self, plugin_id, target, output):
        use_stdout = str(output) == "-"

        try:
            IPAddress(target)
            is_ip = True
        except AddrFormatError:
            is_ip = False

        plugin = Plugin.objects.get(plugin_id=plugin_id)
        callback_kwargs = (
            {
                "entrypoint": self.override_entrypoint,
                "environment": {"PLUGIN_ID": plugin.plugin_id},
                "network": settings.DOCKER_NETWORK,
                "volumes": [f'{(self.plugins_dir / "entrypoint" / "main").absolute()}:{self.override_entrypoint}'],
            }
            if not use_stdout
            else {}
        )

        format_map = {"nameserver": "1.1.1.1", "ip_address|hostname": target}

        if is_ip:
            format_map["ip_address"] = target
        else:
            format_map["hostname"] = target

        return docker.from_env().containers.run(
            image=plugin.oci_image,
            name=f"{plugin.plugin_id}_{datetime.datetime.now(timezone.utc).timestamp()}",
            command=[
                # TODO: add nameserver through configuration later
                arg.format_map(format_map)
                for arg in plugin.oci_arguments
            ],
            stdout=use_stdout,
            stderr=True,
            remove=True,
            **callback_kwargs,
        )


class Command(BaseCommand):
    help = "Run a plugin."

    def add_arguments(self, parser):
        parser.add_argument("plugin_id", type=str)
        parser.add_argument("target", type=str)
        parser.add_argument("--output", "-o", dest="output", type=str, default="file")

    def handle(self, plugin_id, target, output, *args, **options):
        logs = PluginRunner().run(plugin_id, target, output)

        if str(output) == "-":
            self.stdout.write(logs.decode())
        else:
            self.stdout.write("Done running plugin")
