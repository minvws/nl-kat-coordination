from django.core.management.base import BaseCommand
from structlog.testing import capture_logs

from plugins.runner import PluginRunner


class Command(BaseCommand):
    help = "Run a plugin."

    def add_arguments(self, parser):
        parser.add_argument("plugin_id", type=str)
        parser.add_argument("targets", type=str, nargs="+")
        parser.add_argument("--output", "-o", dest="output", type=str, default="file")
        parser.add_argument("--keep-container", "-k", dest="keep", action="store_true", help="Do not remove the container after running the plugin. Useful for debugging.")
        parser.add_argument("--cli", "-c", dest="cli", action="store_true", help="Do not actually run the plugin container but dump the equivalent docker run command. Useful for debugging. Note: to run the command, make sure to set the OPENKAT_TOKEN environment variable first to a personal auth token")

    def handle(self, plugin_id, targets, output, keep, cli, *args, **options):
        with capture_logs():
            logs = PluginRunner().run(plugin_id, targets, output, keep=keep, cli=cli)

        if str(output) == "-":
            self.stdout.write(logs)
        else:
            self.stdout.write("Done running plugin")
