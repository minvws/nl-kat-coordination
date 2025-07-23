import tagulous.admin
from django.contrib import admin, messages
from django.http import HttpResponseRedirect

from openkat.exceptions import OpenKATError
from openkat.models import Indemnification, Organization, OrganizationMember, OrganizationTag


class OrganizationAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "tags"]

    def add_view(self, request, *args, **kwargs):
        try:
            return super().add_view(request, *args, **kwargs)
        except OpenKATError as e:
            self.message_user(request, str(e), level=messages.ERROR)
            return HttpResponseRedirect(request.get_full_path())

    def get_readonly_fields(self, request, obj=None):
        # Obj is None when adding an organization and in that case we don't make
        # code read only so it is possible to specify the code when creating an
        # organization, but code must be read only after the organization
        # objecht has been created.
        if obj:
            return ["code"]
        else:
            return []


@admin.register(OrganizationMember)
class OrganizationMemberAdmin(admin.ModelAdmin):
    list_display = ("user", "organization")


@admin.register(Indemnification)
class IndemnificationAdmin(admin.ModelAdmin):
    list_display = ("organization", "user")

    def get_readonly_fields(self, request, obj=None):
        if not request.user.is_superuser:
            return [f.name for f in self.model._meta.fields]
        else:
            return []


@admin.register(OrganizationTag)
class OrganizationTagAdmin(admin.ModelAdmin):
    pass


tagulous.admin.register(Organization, OrganizationAdmin)
