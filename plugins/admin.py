from django.contrib import admin

from plugins.models import EnabledPlugin, Plugin, PluginSettings

admin.site.register(Plugin)
admin.site.register(PluginSettings)
admin.site.register(EnabledPlugin)
