import json
from json import JSONDecodeError

from django.contrib import admin
from django.db.models import JSONField
from django.forms import widgets

from tools.models import (
    Organization,
    OrganizationMember,
    Indemnification,
    OOIInformation,
)


class JSONInfoWidget(widgets.Textarea):
    # neater way of displaying json field
    def format_value(self, value):
        try:
            value = json.dumps(json.loads(value), indent=2, sort_keys=True)
            # these lines will try to adjust size of TextArea to fit to content
            row_lengths = [len(r) for r in value.split("\n")]
            self.attrs["rows"] = min(max(len(row_lengths) + 2, 10), 30)
            self.attrs["cols"] = min(max(max(row_lengths) + 2, 40), 120)
            return value
        except JSONDecodeError:
            return super().format_value(value)


class OOIInformationAdmin(admin.ModelAdmin):

    # makes sure that the order stays the same
    fields = ("id", "data", "consult_api")

    # better layout of Json field
    formfield_overrides = {JSONField: {"widget": JSONInfoWidget}}

    # if pk is not readonly, it will create a new record upon editing
    def get_readonly_fields(self, request, obj=None):
        if obj is not None:  # editing an existing object
            if obj.value == "":
                return self.readonly_fields + (
                    "id",
                    "consult_api",
                )
            return self.readonly_fields + ("id",)
        return self.readonly_fields


class OrganizationAdmin(admin.ModelAdmin):
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


class OrganizationMemberAdmin(admin.ModelAdmin):
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


class IndemnificationAdmin(admin.ModelAdmin):
    list_display = ("organization", "user")

    def get_readonly_fields(self, request, obj=None):
        if not request.user.is_superuser:
            return [f.name for f in self.model._meta.fields]
        else:
            return []

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


admin.site.register(Organization, OrganizationAdmin)
admin.site.register(OrganizationMember, OrganizationMemberAdmin)
admin.site.register(Indemnification, IndemnificationAdmin)
admin.site.register(OOIInformation, OOIInformationAdmin)
