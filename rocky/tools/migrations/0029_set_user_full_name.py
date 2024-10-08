# Generated by Django 3.2.18 on 2023-02-27 14:44

from django.db import migrations


def set_full_name(apps, schema_editor):
    OrganizationMember = apps.get_model("tools", "OrganizationMember")

    # Set the user full name to the name in OrganizationMember if full_name is
    # empty but the OrganizationMember name isn't.
    for member in OrganizationMember.objects.filter(user__full_name="").exclude(member_name=""):
        member.user.full_name = member.member_name
        member.user.save()


class Migration(migrations.Migration):
    dependencies = [("account", "0001_initial"), ("tools", "0028_auto_20230117_1242")]

    operations = [migrations.RunPython(set_full_name)]
