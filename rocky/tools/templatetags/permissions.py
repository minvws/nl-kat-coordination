from account.models import KATUser
from django import template

from tools.models import Organization, OrganizationMember

register = template.Library()


@register.simple_tag()
def has_organization_perms(perms: str, user: KATUser, organization: Organization = None) -> bool:
    if user.has_perms(perms):
        return True
    if organization:
        member = OrganizationMember.objects.get(user=user, organization=organization)
        return member.has_member_perms(perms)
    members = OrganizationMember.objects.filter(user=user)
    for member in members:
        if member.has_member_perms(perms):
            return True
    return False
