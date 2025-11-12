from django.contrib.auth.mixins import PermissionRequiredMixin
from django.views.generic import CreateView, DeleteView, UpdateView
from rest_framework.permissions import DjangoModelPermissions

from objects.models import object_type_by_name


class KATModelPermissions(DjangoModelPermissions):
    # We change the permissions map to include the view permissions for GET/OPTIONS/HEAD.
    perms_map = {
        "GET": ["%(app_label)s.view_%(model_name)s"],
        "OPTIONS": ["%(app_label)s.view_%(model_name)s"],
        "HEAD": ["%(app_label)s.view_%(model_name)s"],
        "POST": ["%(app_label)s.add_%(model_name)s"],
        "PUT": ["%(app_label)s.change_%(model_name)s"],
        "PATCH": ["%(app_label)s.change_%(model_name)s"],
        "DELETE": ["%(app_label)s.delete_%(model_name)s"],
    }

    def has_permission(self, request, view):
        """Support for stateless JWT auth permissions"""

        if not hasattr(request, "auth") or not isinstance(request.auth, dict):
            return super().has_permission(request, view)

        token_perms = request.auth.get("permissions", []) or []

        queryset = self._queryset(view)
        view_perms = self.get_required_permissions(request.method, queryset.model)

        for view_perm in view_perms:
            if view_perm not in token_perms:
                return super().has_permission(request, view)

        # The auth token has all required permissions
        return True


class KATMultiModelPermissions(KATModelPermissions):
    def has_permission(self, request, view):
        if not request.user or (not request.user.is_authenticated and self.authenticated_users_only):
            return False

        if getattr(view, "_ignore_model_permissions", False):
            return True

        perms: list[str] = []
        models = {key.lower(): model for key, model in object_type_by_name().items()}

        for key in request.data:
            perms.extend(self.get_required_permissions(request.method, models[key]))

        return request.user.has_perms(perms)


class KATModelPermissionRequiredMixin(PermissionRequiredMixin):
    """DRF-like behavior for regular views, inferred not by the HTTP method but by the view type."""

    perms_map = {
        CreateView.__name__: ["%(app_label)s.add_%(model_name)s"],
        UpdateView.__name__: ["%(app_label)s.change_%(model_name)s"],
        DeleteView.__name__: ["%(app_label)s.delete_%(model_name)s"],
    }

    def get_permission_required(self) -> list[str]:
        permissions_required: list[str] = []

        if not issubclass(self.__class__, CreateView | UpdateView | DeleteView):
            return list(super().get_permission_required())

        kwargs = {"app_label": self.model._meta.app_label, "model_name": self.model._meta.model_name}

        if issubclass(self.__class__, CreateView):
            permissions_required.extend([perm % kwargs for perm in self.perms_map[CreateView.__name__]])

        if issubclass(self.__class__, UpdateView):
            permissions_required.extend([perm % kwargs for perm in self.perms_map[UpdateView.__name__]])

        if issubclass(self.__class__, DeleteView):
            permissions_required.extend([perm % kwargs for perm in self.perms_map[DeleteView.__name__]])

        return permissions_required
