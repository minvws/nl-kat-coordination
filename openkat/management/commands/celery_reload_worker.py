import logging
import shlex
import subprocess

from django.core.management.base import BaseCommand
from django.utils import autoreload

logger = logging.getLogger(__name__)


def restart_celery(celery_cmd: str):
    logger.info("Stopping celery")
    cmd = shlex.split(celery_cmd)
    subprocess.call(shlex.split(f"celery -A {cmd[2]} control shutdown -t 2"))

    logger.info("Starting celery worker")
    subprocess.call(cmd)


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("celery_cmd", type=str, help="The celery command to run.")

    def handle(self, celery_cmd: str, *args, **kwargs):
        logger.info("Starting celery worker with autoreload...")

        autoreload.run_with_reloader(restart_celery, celery_cmd)
