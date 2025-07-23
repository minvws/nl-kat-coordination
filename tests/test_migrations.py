from io import StringIO

import pytest
from django.core.management import call_command

pytestmark = pytest.mark.django_db


def test_for_missing_migrations():
    output = StringIO()
    call_command("makemigrations", no_input=True, dry_run=True, stdout=output)
    lines = output.getvalue().strip().splitlines()

    assert lines[0] == "No changes detected"
