from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from account.mixins import OrganizationView


class SuperOrAdminUserRequiredMixin(LoginRequiredMixin, UserPassesTestMixin, OrganizationView):
    def test_func(self):
        return self.request.user.is_superuser or self.organization_member.is_admin


class RedTeamUserRequiredMixin(LoginRequiredMixin, UserPassesTestMixin, OrganizationView):
    def test_func(self):
        return self.organization_member.is_redteam
