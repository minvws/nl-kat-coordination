from django.contrib.auth.mixins import PermissionRequiredMixin
from django.views.generic import CreateView, DeleteView, UpdateView
from rest_framework.permissions import DjangoModelPermissions


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


class KATModelPermissionRequiredMixin(PermissionRequiredMixin):
    perms_map = {
        CreateView.__name__: ["%(app_label)s.add_%(model_name)s"],
        UpdateView.__name__: ["%(app_label)s.change_%(model_name)s"],
        DeleteView.__name__: ["%(app_label)s.delete_%(model_name)s"],
    }

    def get_permission_required(self):
        permissions_required = []

        if not issubclass(self.__class__, CreateView | UpdateView | DeleteView):
            return permissions_required

        kwargs = {"app_label": self.model._meta.app_label, "model_name": self.model._meta.model_name}

        if issubclass(self.__class__, CreateView):
            permissions_required.extend([perm % kwargs for perm in self.perms_map[CreateView.__name__]])

        if issubclass(self.__class__, UpdateView):
            permissions_required.extend([perm % kwargs for perm in self.perms_map[CreateView.__name__]])

        if issubclass(self.__class__, DeleteView):
            permissions_required.extend([perm % kwargs for perm in self.perms_map[CreateView.__name__]])

        return permissions_required
