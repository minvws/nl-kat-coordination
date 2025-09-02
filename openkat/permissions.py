from rest_framework import exceptions
from rest_framework.permissions import BasePermission, DjangoModelPermissions

from octopoes.models import OOI
from openkat.views.mixins import OOIList


# This is a bit clunky, but DRF doesn't allow you to specify a permission
# directly, only a Permission class
class CanRecalculateBits(BasePermission):
    def has_permission(self, request, view) -> bool:
        return request.user.has_perm("openkat.can_recalculate_bits")


class CanSetKatalogusSettings(BasePermission):
    def has_permission(self, request, view) -> bool:
        return request.user.has_perm("openkat.can_set_katalogus_settings")


class KATModelPermissions(DjangoModelPermissions):
    # We change the permissions map to include the view permissions for
    # GET/OPTIONS/HEAD.
    perms_map = {
        "GET": ["%(app_label)s.view_%(model_name)s"],
        "OPTIONS": ["%(app_label)s.view_%(model_name)s"],
        "HEAD": ["%(app_label)s.view_%(model_name)s"],
        "POST": ["%(app_label)s.add_%(model_name)s"],
        "PUT": ["%(app_label)s.change_%(model_name)s"],
        "PATCH": ["%(app_label)s.change_%(model_name)s"],
        "DELETE": ["%(app_label)s.delete_%(model_name)s"],
    }

    def get_required_permissions(self, method, model_cls):
        """Specialized version handling OOIs, that do not have the _meta property"""
        if method not in self.perms_map:
            raise exceptions.MethodNotAllowed(method)

        if model_cls == OOI or issubclass(model_cls, OOI):
            kwargs = {"app_label": "openkat", "model_name": "ooi"}

            return [perm % kwargs for perm in self.perms_map[method]]

        return super().get_required_permissions(method, model_cls)

    def has_permission(self, request, view):
        """Specialized version handling an OOIList queryset that does not have the model property"""

        if not request.user or (not request.user.is_authenticated and self.authenticated_users_only):
            return False

        if getattr(view, "_ignore_model_permissions", False):
            return True

        queryset = self._queryset(view)

        if isinstance(queryset, OOIList):
            perms = self.get_required_permissions(request.method, OOI)
        else:
            perms = self.get_required_permissions(request.method, queryset.model)

        return request.user.has_perms(perms)
