import datetime
from datetime import timezone

import docker
from django.conf import settings
from django.core.management.base import BaseCommand

from plugins.models import Plugin


class Command(BaseCommand):
    help = "Run a plugin."
    OVERRIDE_ENTRYPOINT = "/bin/runner"
    PLUGINS_DIR = settings.BASE_DIR / "plugins" / "plugins"

    def add_arguments(self, parser):
        parser.add_argument("plugin_id", type=str)
        parser.add_argument("target", type=str)
        parser.add_argument("--output", "-o", dest="output", type=str, default="file")

    def handle(self, plugin_id, target, output, *args, **options):
        use_stdout = str(output) == "-"
        plugin = Plugin.objects.get(plugin_id=plugin_id)
        docker_client = docker.from_env()

        callback_kwargs = (
            {
                "entrypoint": self.OVERRIDE_ENTRYPOINT,
                "environment": {"PLUGIN_ID": plugin.plugin_id},
                "network": settings.DOCKER_NETWORK,
                "volumes": [f'{(self.PLUGINS_DIR / "entrypoint" / "main").absolute()}:{self.OVERRIDE_ENTRYPOINT}'],
            }
            if not use_stdout
            else {}
        )

        logs = docker_client.containers.run(
            image=plugin.oci_image,
            name=f"{plugin.plugin_id}_{datetime.datetime.now(timezone.utc).timestamp()}",
            command=[
                # TODO: add nameserver through configuration later
                arg.format_map({"hostname": target, "nameserver": "1.1.1.1", "ip_address": target})
                for arg in plugin.oci_arguments
            ],
            stdout=use_stdout,
            stderr=True,
            remove=True,
            **callback_kwargs,
        )

        if use_stdout:
            self.stdout.write(logs.decode())
        else:
            self.stdout.write("Done running plugin")
