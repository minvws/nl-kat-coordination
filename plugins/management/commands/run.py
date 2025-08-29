from django.core.management.base import BaseCommand

from plugins.runner import PluginRunner


class Command(BaseCommand):
    help = "Run a plugin."

    def add_arguments(self, parser):
        parser.add_argument("plugin_id", type=str)
        parser.add_argument("target", type=str, default="")
        parser.add_argument("--output", "-o", dest="output", type=str, default="file")

    def handle(self, plugin_id, target, output, *args, **options):
        logs = PluginRunner().run(plugin_id, target or None, output)

        if str(output) == "-":
            self.stdout.write(logs.decode())
        else:
            self.stdout.write("Done running plugin")
