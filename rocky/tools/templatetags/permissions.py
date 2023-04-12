from django import template
from tools.models import Organization, OrganizationMember
from account.models import KATUser

register = template.Library()


@register.simple_tag()
def has_organization_perm(perm: str, user: KATUser, organization: Organization):
    member = OrganizationMember.objects.get(user=user, organization=organization)
    return user.has_perm(perm) or member.has_member_perm(perm)
