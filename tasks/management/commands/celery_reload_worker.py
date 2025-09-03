import logging
import os
import shlex
import signal
import subprocess
import sys

from django.core.management.base import BaseCommand
from django.utils.autoreload import DJANGO_AUTORELOAD_ENV, get_reloader, start_django, restart_with_reloader

from tasks.celery import cancel_all_tasks

logger = logging.getLogger(__name__)


def restart_celery(celery_cmd: str):
    logger.info("Stopping celery")
    cmd = shlex.split(celery_cmd)
    subprocess.call(shlex.split(f"celery -A {cmd[2]} control shutdown -t 2"))

    logger.info("Starting celery worker")
    subprocess.call(cmd)


def run_with_reloader(main_func, *args, **kwargs):
    def handle(*args):
        cancel_all_tasks()
        sys.exit(0)

    signal.signal(signal.SIGTERM, handle)

    try:
        if os.environ.get(DJANGO_AUTORELOAD_ENV) == "true":
            reloader = get_reloader()
            logger.info(
                "Watching for file changes with %s", reloader.__class__.__name__
            )
            start_django(reloader, main_func, *args, **kwargs)
        else:
            exit_code = restart_with_reloader()
            sys.exit(exit_code)
    except KeyboardInterrupt:
        pass


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("celery_cmd", type=str, help="The celery command to run.")

    def handle(self, celery_cmd: str, *args, **kwargs):
        logger.info("Starting celery worker with autoreload...")

        run_with_reloader(restart_celery, celery_cmd)
