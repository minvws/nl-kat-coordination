from account.mixins import MemberPermissionMixin
from django import template

from tools.models import OrganizationMember

register = template.Library()


@register.simple_tag()
def has_organization_perms(perm: str, organization_member: OrganizationMember) -> bool:
    if organization_member.user.has_perms(perm):
        return True
    return MemberPermissionMixin().has_member_perms(perm, organization_member)
