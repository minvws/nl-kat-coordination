import csv
import io
import logging

from account.forms import OrganizationMemberToGroupAddForm, PasswordResetForm
from account.mixins import OrganizationPermissionRequiredMixin, OrganizationView
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ObjectDoesNotExist
from django.http import FileResponse
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.urls.base import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic.edit import CreateView, FormView
from tools.forms.upload_csv import UploadCSVForm
from tools.models import OrganizationMember

logger = logging.getLogger(__name__)

User = get_user_model()


MEMBER_UPLOAD_COLUMNS = [
    "full_name",
    "email",
    "account_type",
    "trusted_clearance_level",
    "acknowledged_clearance_level",
]
CSV_CRITERIA = [
    _("Add column titles. Followed by each object on a new line."),
    _("The columns are: ") + ", ".join(MEMBER_UPLOAD_COLUMNS),
]


class OrganizationMemberAddView(OrganizationPermissionRequiredMixin, OrganizationView, CreateView):
    """
    View to create a new member for a specific organization.
    """

    model = User
    template_name = "organizations/organization_member_add.html"
    form_class = OrganizationMemberToGroupAddForm
    permission_required = "tools.add_organizationmember"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["organization_code"] = self.organization.code
        return kwargs

    def get_success_url(self, **kwargs):
        return reverse_lazy("organization_member_list", kwargs={"organization_code": self.organization.code})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [
            {
                "url": reverse("organization_member_list", kwargs={"organization_code": self.organization.code}),
                "text": "Members",
            },
            {
                "url": reverse(
                    "organization_member_add",
                    kwargs={"organization_code": self.organization.code},
                ),
                "text": _("Add member"),
            },
        ]
        context["organization"] = self.organization

        return context

    def form_valid(self, form):
        self.add_success_notification()
        return super().form_valid(form)

    def add_success_notification(self):
        success_message = _("Member added successfully.")
        messages.add_message(self.request, messages.SUCCESS, success_message)


class DownloadMembersTemplateView(OrganizationPermissionRequiredMixin, OrganizationView):
    permission_required = "tools.add_organizationmember"

    def get(self, request, **kwargs):
        """Create a csv file with the right columns to download as a template for uploading organization members"""

        template = ",".join(MEMBER_UPLOAD_COLUMNS)

        return FileResponse(io.BytesIO(template.encode()), filename=f"{self.organization}_organization_members.csv")


class MembersUploadView(OrganizationPermissionRequiredMixin, OrganizationView, FormView):
    template_name = "organizations/organization_member_upload.html"
    form_class = UploadCSVForm
    permission_required = "tools.add_organizationmember"

    def get_success_url(self):
        return reverse_lazy("organization_member_list", kwargs={"organization_code": self.organization.code})

    def form_valid(self, form):
        self.process_csv(form)
        return super().form_valid(form)

    def process_csv(self, form) -> None:
        csv_raw_data = form.cleaned_data["csv_file"].read()
        csv_data = io.StringIO(csv_raw_data.decode("UTF-8"))

        try:
            for row in csv.DictReader(csv_data, delimiter=",", quotechar='"'):
                if not row:
                    continue  # skip empty lines

                try:
                    full_name, email, account_type, trusted_clearance_level, acknowledged_clearance_level = (
                        row["full_name"],
                        row["email"],
                        row["account_type"],
                        row["trusted_clearance_level"],
                        row["acknowledged_clearance_level"],
                    )
                except KeyError:
                    messages.add_message(self.request, messages.ERROR, _("The csv file is missing required columns"))
                    return redirect("organization_member_upload", self.organization.code)

                user, user_created = User.objects.get_or_create(email=email, defaults={"full_name": full_name})

                if user_created:
                    form = PasswordResetForm({"email": email})

                    if not form.is_valid():
                        logger.warning("Email not valid: %s", email)
                        continue

                    form.save(
                        email_template_name="registration_email.html",
                        subject_template_name="registration_subject.txt",
                        extra_email_context={"organization": self.organization.name},
                        use_https=self.request.is_secure(),
                        request=self.request,
                    )

                try:
                    member, member_created = OrganizationMember.objects.get_or_create(
                        user=user,
                        organization=self.organization,
                        defaults={
                            "organization": self.organization,
                            "status": OrganizationMember.STATUSES.ACTIVE,
                            "trusted_clearance_level": trusted_clearance_level,
                            "acknowledged_clearance_level": acknowledged_clearance_level,
                        },
                    )
                except Exception:
                    if user_created:
                        user.delete()

                    raise

                try:
                    member.groups.add(Group.objects.get(name=account_type))
                except ObjectDoesNotExist:
                    logger.error("Group does not exist")
                    continue

            messages.add_message(self.request, messages.SUCCESS, _("Successfully processed users from csv."))
        except csv.Error:
            messages.add_message(
                self.request, messages.ERROR, _("Error parsing the csv file. Please verify its contents.")
            )
            logger.exception("Failed handling csv file")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["criteria"] = CSV_CRITERIA

        return context
