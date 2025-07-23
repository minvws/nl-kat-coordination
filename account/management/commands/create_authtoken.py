import sys

from django.core.management import BaseCommand
from django.db.utils import IntegrityError

from account.models import AuthToken, KATUser


class Command(BaseCommand):
    help = "Creates a new authentication token."

    def add_arguments(self, parser):
        parser.add_argument("username", help="Username to create the token for")
        parser.add_argument("name", help="Name of the token")

    def handle(self, *args, **options):
        try:
            user = KATUser.objects.get(email=options["username"])
        except KATUser.DoesNotExist:
            self.stderr.write(self.style.ERROR(f"Username {options['username']} not found"))

            sys.exit(1)

        auth_token = AuthToken(user=user, name=options["name"])
        token = auth_token.generate_new_token()
        try:
            auth_token.save()
        except IntegrityError as e:
            if 'unique constraint "unique name"' in e.args[0]:
                self.stderr.write(
                    self.style.ERROR(f"There already exists a token with name {options['name']} for user {user}")
                )
                sys.exit(1)
            else:
                raise

        if options["verbosity"] >= 1:
            self.stdout.write(
                self.style.SUCCESS(f"Successfully created token {token} with name {options['name']} for user {user}")
            )
        else:
            self.stdout.write(token)
