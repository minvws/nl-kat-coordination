from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from tools.models import GROUP_ADMIN, GROUP_REDTEAM


class SuperOrAdminUserRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        is_admin = self.request.user.groups.filter(name=GROUP_ADMIN).exists()
        return self.request.user.is_superuser or is_admin


class RedTeamUserRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.groups.filter(name=GROUP_REDTEAM).exists()
