from django import forms
from django.utils.translation import gettext_lazy as _
from tools.models import Organization, OrganizationMember
from tools.forms.settings import BLANK_CHOICE


class OrganizationListForm(forms.Form):
    """
    Creates a dropdown list of Organizations of a particular member.
    """

    error_messages = {
        "required": _("Organization is required."),
    }

    def __init__(self, user, exclude_organization=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.exclude_organization = exclude_organization
        self.populate_dropdown_list(user)

    def populate_dropdown_list(self, user):
        organizations = []

        members = OrganizationMember.objects.filter(user=user)

        for member in members:
            organization = Organization.objects.get(name=member.organization)

            if not self.exclude_organization or organization != self.exclude_organization:
                organizations.append([organization.code, organization.name])

        if organizations:
            props = {
                "required": True,
                "label": _("Organizations"),
                "help_text": _("The organization from which to clone settings."),
                "error_messages": self.error_messages,
            }
            self.fields["organization"] = forms.ChoiceField(**props)
            self.fields["organization"].choices = [BLANK_CHOICE] + organizations
