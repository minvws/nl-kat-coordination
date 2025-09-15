from typing import TYPE_CHECKING

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from openkat.models import Organization, User

if TYPE_CHECKING:
    from django.db.models.query import QuerySet
    from django.http import HttpRequest


@admin.register(User)
class UserAdmin(BaseUserAdmin[User]):  # type: ignore[type-var]
    list_display = ("email", "full_name", "is_staff", "is_active", "date_joined")
    list_filter = ("is_staff", "is_active", "date_joined")
    search_fields = ("email", "full_name")
    ordering = ("email",)

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (_("Personal info"), {"fields": ("full_name",)}),
        (_("Permissions"), {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = ((None, {"classes": ("wide",), "fields": ("email", "full_name", "password1", "password2")}),)

    def get_queryset(self, request: "HttpRequest") -> "QuerySet[User]":
        return super().get_queryset(request)


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin[Organization]):
    list_display = ("name",)
    search_fields = ("name",)
    ordering = ("name",)

    def get_queryset(self, request: "HttpRequest") -> "QuerySet[Organization]":
        return super().get_queryset(request)
