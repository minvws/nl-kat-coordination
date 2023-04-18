from django import template
from tools.models import Organization, OrganizationMember
from account.models import KATUser

register = template.Library()


@register.simple_tag()
def has_organization_perm(perm: str, user: KATUser, organization: Organization) -> bool:
    if user.has_perm(perm):
        return True
    if organization:
        member = OrganizationMember.objects.get(user=user, organization=organization)
        return member.has_member_perm(perm)
    members = OrganizationMember.objects.filter(user=user)
    for member in members:
        if member.has_member_perm(perm):
            return True
    return False
