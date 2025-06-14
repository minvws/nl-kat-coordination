# Generated by Django 5.0.13 on 2025-04-07 12:07

from django.db import migrations
from tools.models import Organization

from crisis_room.management.commands.dashboards import run_findings_dashboard


def create_findings_dashboard_for_all_orgs(_apps, _schema_editor):
    for organization in Organization.objects.all():
        run_findings_dashboard(organization)


class Migration(migrations.Migration):
    dependencies = [("crisis_room", "0001_initial")]

    operations = [migrations.RunPython(create_findings_dashboard_for_all_orgs)]
