from django import template

from tools.models import Organization, OrganizationMember

register = template.Library()


@register.simple_tag
def get_organizations(user):
    if user.is_superuser:
        return Organization.objects.all()
    organizations = []
    members = OrganizationMember.objects.filter(user=user)
    if members.exists():
        for member in members:
            if member.status != "blocked":
                organization = Organization.objects.get(name=member.organization)
                organizations.append(organization)
        return organizations
