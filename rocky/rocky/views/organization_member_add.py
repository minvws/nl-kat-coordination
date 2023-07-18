import csv
import io

from account.forms import OrganizationMemberToGroupAddForm
from account.mixins import OrganizationPermissionRequiredMixin, OrganizationView
from tools.forms.upload_member import UploadMemberForm
from tools.models import OrganizationMember

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse_lazy
from django.urls.base import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic.edit import CreateView, FormView

User = get_user_model()


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


class MemberUpload(OrganizationPermissionRequiredMixin, OrganizationView, FormView):
    template_name = "organizations/organization_member_add.html"
    form_class = UploadMemberForm
    permission_required = "tools.add_organizationmember"

    def get_success_url(self):
        return reverse_lazy("organization_member_list", kwargs={"organization_code": self.organization.code})

    def form_valid(self, form):
        if not self.process_csv(form):
            return self.get(self.request, *self.args, **self.kwargs)

        return super().form_valid(form)

    def process_csv(self, form):
        csv_raw_data = form.cleaned_data["csv_file"].read()
        csv_data = io.StringIO(csv_raw_data.decode("UTF-8"))

        rows_with_error = []
        try:
            for row_number, row in enumerate(csv.DictReader(csv_data, delimiter=",", quotechar='"'), start=1):
                if not row:
                    continue  # skip empty lines
                try:
                    full_name, email, account_type, trusted_clearance_level, acknowledged_clearance_level = (
                        row["full_name"],
                        row["email"],
                        row["account_type"],
                        row.get("trusted_clearance_level", 0),
                        row.get("acknowledged_clearance_level", 0)
                    )

                    user, created = User.objects.get_or_create(
                        full_name=full_name,
                        email=email,
                    )

                    member = OrganizationMember.objects.create(
                        user=user,
                        organization=self.organization,
                        trusted_clearance_level=trusted_clearance_level,
                        acknowledged_clearance_level=acknowledged_clearance_level,
                    )

                    group = Group.objects.get(name=account_type)
                    member.groups.add(group)

                    user.save()
                    member.save()
                except KeyError:
                    rows_with_error.append(row_number)

            if rows_with_error:
                message = _("Object(s) could not be created for row number(s): ") + ", ".join(map(str, rows_with_error))
                return self.add_error_notification(message)

            self.add_success_notification(_("Object(s) successfully added."))
        except (csv.Error, IndexError):
            return self.add_error_notification(CSV_ERRORS["csv_error"])
