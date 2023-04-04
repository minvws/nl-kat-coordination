from django import template
from tools.models import OrganizationMember

register = template.Library()


@register.simple_tag()
def has_member_perm(perm: str, member: OrganizationMember):
    if member:
        return member.has_member_perm(perm)
