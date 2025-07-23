from rest_framework.permissions import BasePermission, DjangoModelPermissions


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
