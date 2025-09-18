import sys

from django.core.management import BaseCommand
from django.db.utils import IntegrityError

from openkat.models import AuthToken, KATUser


def create_auth_token(username, token_name):
    user = KATUser.objects.get(email=username)
    auth_token = AuthToken(user=user, name=token_name)
    token = auth_token.generate_new_token()
    auth_token.save()

    return auth_token, token


class Command(BaseCommand):
    help = "Creates a new authentication token."

    def add_arguments(self, parser):
        parser.add_argument("username", help="Username to create the token for")
        parser.add_argument("token_name", help="Name of the token")

    def handle(self, username, token_name, verbosity, **kwargs):
        try:
            auth_token, token = create_auth_token(username=username, token_name=token_name)
        except KATUser.DoesNotExist:
            self.stderr.write(self.style.ERROR(f"Username {username} not found"))
            sys.exit(1)
        except IntegrityError as e:
            if 'unique constraint "unique name"' in e.args[0]:
                self.stderr.write(
                    self.style.ERROR(f"There already exists a token with name {token_name} for this user")
                )
                sys.exit(1)
            else:
                raise

        if verbosity >= 1:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully created token {token} with name {token_name} for user {auth_token.user}"
                )
            )
        else:
            self.stdout.write(token)
