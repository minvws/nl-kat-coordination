from django.contrib import admin

from katalogus.forms import PluginDeepLinkForm
from katalogus.models import OrganizationPlugin, PluginDeepLink


class PluginDeepLinkAdmin(admin.ModelAdmin):
    form = PluginDeepLinkForm


class OrganizationPluginAdmin(admin.ModelAdmin):
    pass


admin.site.register(PluginDeepLink, PluginDeepLinkAdmin)
admin.site.register(OrganizationPlugin, OrganizationPluginAdmin)
