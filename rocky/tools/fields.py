from django.db import models


class LowerCaseSlugField(models.SlugField):
    def to_python(self, value):
        if value is None:
            return None
        return value.lower()
