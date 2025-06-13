import json
from datetime import datetime, timezone

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
                new_column_settings = [column_value for column_value, _ in columns.items()]
                item.settings["columns"] = new_column_settings
                item.save()


def change_query_params(_apps, _schema_editor):
    dashboard_items = DashboardItem.objects.all()
    new_query = {}
    for dashboard_item in dashboard_items:
        if dashboard_item.query:
            query = json.loads(dashboard_item.query)
            new_query["observed_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            new_query["ooi_type"] = query.get("ooi_types", [])
            new_query["clearance_level"] = query.get("scan_level", [])
            new_query["clearance_type"] = query.get("scan_profile_type", [])
            new_query["search"] = query.get("search_string", "")
            new_query["order_by"] = query.get("order_by", "object_type")
            new_query["sorting_order"] = query.get("asc_desc", "asc")
            new_query["limit"] = query.get("limit", 20)

            dashboard_item.query = json.dumps(new_query)
            dashboard_item.save()


class Migration(migrations.Migration):
    dependencies = [("crisis_room", "0005_add_dashboard_permissions_to_groups")]

    operations = [
        migrations.RenameModel(old_name="DashboardData", new_name="DashboardItem"),
        migrations.RenameField(model_name="dashboarditem", old_name="query_from", new_name="source"),
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
        migrations.RunPython(change_query_params),
    ]
