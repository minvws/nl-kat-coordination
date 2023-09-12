import inspect

from django.conf import global_settings, settings
from pydantic import BaseSettings, PyObject


class SetUp(BaseSettings):
    DJANGO_SETTINGS_MODULE: PyObject = "rocky.settings.DjangoSettings"

    def configure(self):
        if settings.configured:
            return False

        settings_obj: BaseSettings
        # The settings module can either be a settings class, or an instance of a
        # settings class.
        if inspect.isclass(self.DJANGO_SETTINGS_MODULE):
            settings_obj = self.DJANGO_SETTINGS_MODULE()
        else:
            settings_obj = self.DJANGO_SETTINGS_MODULE

        settings_dict = {
            key: value
            for key, value in settings_obj.dict().items()
            if key == key.upper()
            and (
                hasattr(global_settings, key) is False
                # Running the test suite can modify settings.DATABASES, so always
                # override the mutable global_settings.DATABASES.
                or key == "DATABASES"
                or value != getattr(global_settings, key)
            )
        }
        settings.configure(**settings_dict)
        return True
