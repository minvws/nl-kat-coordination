from getpass import getpass

from django.conf import settings
from django.contrib.auth import authenticate
from django.core.management import BaseCommand
from django.db import transaction
from structlog.testing import capture_logs

from openkat.management.commands.create_authtoken import create_auth_token
from openkat.models import AuthToken


class Command(BaseCommand):
    help = "Creates a new authentication token."

    def add_arguments(self, parser):
        parser.add_argument("--username", type=str, help="Username for authentication")
        parser.add_argument(
            "--password", type=str, help="Password for authentication (optional, will prompt if not provided)"
        )

    def handle(self, *args, **options):
        with capture_logs():
            username = options.get("username")
            password = options.get("password")

            if not username:
                username = getpass("# Username: ")
            if not password:
                password = getpass("# Password: ")

            user = authenticate(username=username, password=password)

            with transaction.atomic():
                AuthToken.objects.filter(user=user, name="local").delete()
                auth_token, token = create_auth_token(username, "local")
                auth_token.save()

            local_env = [
                f"OPENKAT_TOKEN={token}",
                "OPENKAT_API=http://localhost:8000/api/v1",
                "OPENKAT_DB_HOST=localhost",
                "OPENKAT_XTDB_HOST=localhost",
                "OPENKAT_XTDB_PORT=5433",
                f"REDIS_QUEUE_URI=redis://:{settings.REDIS_PASSWORD}@localhost:6379/0",
            ]

            local_env_file = settings.BASE_DIR / ".env.local"
            local_env_file.write_text("\n".join(local_env))

            for line in local_env:
                self.stdout.write(f"export {line}")
