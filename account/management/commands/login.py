from getpass import getpass

from django.conf import settings
from django.contrib.auth import authenticate
from django.core.management import BaseCommand
from django.db import transaction

from account.management.commands.create_authtoken import create_auth_token
from account.models import AuthToken


class Command(BaseCommand):
    help = "Creates a new authentication token."

    def add_arguments(self, parser):
        parser.add_argument("username", help="Username to create the token for")

    def handle(self, username, **kwargs):
        password = getpass(f"Password for {username}:")
        user = authenticate(username=username, password=password)

        with transaction.atomic():
            AuthToken.objects.filter(user=user, name="local").delete()
            auth_token, token = create_auth_token(username, "local")
            auth_token.save()

        local_env = f"OPENKAT_TOKEN={token}\n"
        local_env += "OPENKAT_API=http://localhost:8000/api/v1\n"
        local_env += "OPENKAT_DB_HOST=localhost\n"

        local_env_file = settings.BASE_DIR / ".env.local"
        local_env_file.write_text(local_env)

        self.stdout.write("Successfully created or updated local env file in .env.local")
