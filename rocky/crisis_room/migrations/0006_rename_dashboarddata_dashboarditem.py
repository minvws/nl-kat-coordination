from django.contrib.auth.models import Permission
from django.db import migrations, models

from crisis_room.models import FINDINGS_DASHBOARD_NAME, Dashboard, DashboardItem


def update_permissions(_apps, _schema_editor):
    old_permissions = Permission.objects.filter(codename__icontains="dashboarddata")

    for permission in old_permissions:
        new_codename = permission.codename.replace("dashboarddata", "dashboarditem")

        if not Permission.objects.filter(codename=new_codename).exists():
            Permission.objects.create(
                name=permission.name.replace("dashboard data", "dashboard item"),
                content_type=permission.content_type,
                codename=new_codename,
            )

        permission.delete()


def change_name_findings_dashboard(_apps, _schema_editor):
    dashboards = Dashboard.objects.filter(name="Findings Dashboard")
    for dashboard in dashboards:
        dashboard.name = FINDINGS_DASHBOARD_NAME
        dashboard.save()


def change_settings_columns(_apps, _schema_editor):
    dashboard_items = DashboardItem.objects.all()

    for item in dashboard_items:
        if item.settings:
            columns = item.settings["columns"]
            if isinstance(columns, dict):
                new_column_settings = [{k: v} for k, v in columns.items()]
                item.settings["columns"] = new_column_settings
                item.save()


class Migration(migrations.Migration):
    dependencies = [("crisis_room", "0005_add_dashboard_permissions_to_groups")]

    operations = [
        migrations.RenameModel(old_name="DashboardData", new_name="DashboardItem"),
        migrations.AlterModelOptions(
            name="dashboarditem",
            options={
                "permissions": [
                    ("change_dashboarditem_position", "Can change position up or down of a dashboard item.")
                ]
            },
        ),
        migrations.AddConstraint(
            model_name="dashboarditem",
            constraint=models.UniqueConstraint(
                condition=models.Q(("findings_dashboard", True)),
                fields=("dashboard",),
                name="unique_findings_dashboard_per_dashboard",
            ),
        ),
        migrations.RunPython(update_permissions),
        migrations.RunPython(change_name_findings_dashboard),
        migrations.RunPython(change_settings_columns),
    ]
