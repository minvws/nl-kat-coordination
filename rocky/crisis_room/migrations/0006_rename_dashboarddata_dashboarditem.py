from django.contrib.auth.models import Permission
from django.db import migrations, models


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
                fields=("findings_dashboard",),
                name="findings_dashboard",
            ),
        ),
        migrations.RunPython(update_permissions),
    ]
