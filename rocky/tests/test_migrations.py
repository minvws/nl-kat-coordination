from io import StringIO

import pytest

from django.core.management import call_command

pytestmark = pytest.mark.django_db


def test_for_missing_migrations():
    output = StringIO()
    call_command("makemigrations", no_input=True, dry_run=True, stdout=output)
    lines = output.getvalue().strip().splitlines()

    # The outcome of makemigrations here depends on having run `makemigrations` in your local environment, which creates
    # a missing migration for two_factor (also see https://github.com/jazzband/django-two-factor-auth/issues/611).

    if len(lines) == 1:
        assert lines[0] == "No changes detected"
    else:
        assert len(lines) == 3
        assert lines[0] == "Migrations for 'two_factor':"
