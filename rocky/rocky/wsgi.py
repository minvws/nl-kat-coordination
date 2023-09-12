"""
WSGI config for rocky project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

from rocky.settings_helper import SetUp

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "rocky.settings.DjangoSettings")
SetUp().configure()

application = get_wsgi_application()
