import json

import docker
from django.conf import settings
from django.core.management.base import BaseCommand

from plugins.models import Plugin


class Command(BaseCommand):
    help = "Run a plugin."
    OVERRIDE_ENTRYPOINT = "/bin/runner"
    PLUGINS_DIR = settings.BASE_DIR / "plugins" / "plugins"

    def add_arguments(self, parser):
        parser.add_argument("plugin", type=str)
        parser.add_argument("inputs", type=str)
        parser.add_argument("--output", "-o", dest="output", type=str, default="file")

    def handle(self, plugin, inputs, output, *args, **options):
        use_stdout = str(output) == "-"

        dns = json.load((self.PLUGINS_DIR / "dns_records.json").open())
        definition = Plugin(
            plugin_id=dns["plugin_id"],
            name=dns["name"],
            description=dns["description"],
            scan_level=dns["scan_level"],
            oci_image=dns["oci_image"],
            oci_arguments=dns["oci_arguments"],
        )

        docker_client = docker.from_env()

        callback_kwargs = {
            "entrypoint": self.OVERRIDE_ENTRYPOINT,
            "environment": {"PLUGIN_ID": definition.plugin_id},
            "network": settings.DOCKER_NETWORK,
            "volumes": [
                f'{(self.PLUGINS_DIR / "entrypoint" / "main").absolute()}:{self.OVERRIDE_ENTRYPOINT}'
            ],
        } if not use_stdout else {}

        logs = docker_client.containers.run(
            image=definition.oci_image,
            name=definition.plugin_id,
            command=[
                # TODO: add nameserver through configuration later
                arg.format_map({"hostname": inputs, "nameserver": "1.1.1.1"}) for arg in definition.oci_arguments
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
