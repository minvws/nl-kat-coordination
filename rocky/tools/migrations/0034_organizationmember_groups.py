# Generated by Django 3.2.18 on 2023-04-26 13:54

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("auth", "0012_alter_user_first_name_max_length"), ("tools", "0033_auto_20230407_1113")]

    operations = [
        migrations.AddField(
            model_name="organizationmember", name="groups", field=models.ManyToManyField(blank=True, to="auth.Group")
        )
    ]
