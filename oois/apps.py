from django.apps import AppConfig


class OOIsConfig(AppConfig):
    default_auto_field = "django_xtdb.patch.XTDBBigAutoField"
    name = "oois"
