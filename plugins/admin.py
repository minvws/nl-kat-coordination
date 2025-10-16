from django.contrib import admin

from plugins.models import Plugin, PluginSettings

admin.site.register(Plugin)
admin.site.register(PluginSettings)
