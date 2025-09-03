from django.core.management.base import BaseCommand
from structlog.testing import capture_logs

from plugins.runner import PluginRunner


class Command(BaseCommand):
    help = "Run a plugin."

    def add_arguments(self, parser):
        parser.add_argument("plugin_id", type=str)
        parser.add_argument("target", type=str, default="")
        parser.add_argument("--output", "-o", dest="output", type=str, default="file")
        parser.add_argument("--keep-container", "-k", dest="keep", action="store_true", help="Do not remove the container after running the plugin. Useful for debugging.")
        parser.add_argument("--cli", "-c", dest="cli", action="store_true", help="Do not actually run the plugin container but dump the equivalent docker run command. Useful for debugging.")

    def handle(self, plugin_id, target, output, keep, cli, *args, **options):
        with capture_logs():
            logs = PluginRunner().run(plugin_id, target or None, output, keep=keep, cli=cli)

        if str(output) == "-":
            self.stdout.write(logs)
        else:
            self.stdout.write("Done running plugin")
