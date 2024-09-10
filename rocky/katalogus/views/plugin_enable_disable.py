from django.contrib import messages
from django.http import HttpResponseRedirect
from django.utils.translation import gettext_lazy as _

from katalogus.views.mixins import SinglePluginView


class PluginEnableDisableView(SinglePluginView):
    def post(self, request, *args, **kwargs):
        plugin_state = kwargs["plugin_state"]

        if plugin_state == "True":
            self.katalogus_client.disable_plugin(self.plugin)
            messages.add_message(
                self.request,
                messages.WARNING,
                _("{} '{}' disabled.").format(self.plugin.type.title(), self.plugin.name),
            )
            return HttpResponseRedirect(request.POST.get("current_url"))

        if self.plugin.can_scan(self.organization_member):
            self.katalogus_client.enable_plugin(self.plugin)
            messages.add_message(
                self.request,
                messages.SUCCESS,
                _("{} '{}' enabled.").format(self.plugin.type.title(), self.plugin.name),
            )
        else:
            member_clearance_level_text = (
                f"Your clearance level is L{self.organization_member.acknowledged_clearance_level}. Contact your "
                f"administrator to get a higher clearance level."
            )

            if (
                self.organization_member.trusted_clearance_level < 0
                or self.organization_member.acknowledged_clearance_level < 0
            ):
                member_clearance_level_text = _(
                    "Your clearance level is not set. Go to your profile page to see your clearance "
                    "or contact the administrator to set a clearance level."
                )

            messages.add_message(
                self.request,
                messages.ERROR,
                _("To enable {} you need at least a clearance level of L{}. " + member_clearance_level_text).format(
                    self.plugin.name.title(),
                    self.plugin.scan_level.value,
                ),
            )

        return HttpResponseRedirect(request.POST.get("current_url"))
