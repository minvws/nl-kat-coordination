from django.conf import settings
from whitenoise.storage import CompressedManifestStaticFilesStorage


class RockyStaticFilesStorage(CompressedManifestStaticFilesStorage):
    def url(self, name, force=False):
        if settings.DEBUG and settings.COMPRESS_ENABLED:
            # If django-compressor is enabled when DEBUG is also enabled, we
            # need to force Django to use the hashed urls so that
            # django-compressor can find the static assets in the offline
            # manifest. This is needed to make it possible to use DEBUG with
            # container images or Debian packages where we only ship the hashed
            # files.
            force = True

        return super().url(name, force)
