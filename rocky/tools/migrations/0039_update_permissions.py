from django.db import migrations

from tools.models import GROUP_CLIENT, GROUP_REDTEAM


def add_group_permissions(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    try:
        redteam = Group.objects.get(name=GROUP_REDTEAM)
        redteam.permissions.add(Permission.objects.get(codename="can_mute_findings"))
        redteam.permissions.add(Permission.objects.get(codename="can_view_katalogus_settings"))
        redteam.permissions.add(Permission.objects.get(codename="can_set_katalogus_settings"))

        clients = Group.objects.get(name=GROUP_CLIENT)
        clients.permissions.add(Permission.objects.get(codename="can_scan_organization"))
    except Group.DoesNotExist:
        pass


class Migration(migrations.Migration):
    dependencies = [
        ("tools", "0039_merge_0038_alter_organization_options_0038_delete_job"),
    ]

    operations = [
        migrations.RunPython(add_group_permissions),
    ]
