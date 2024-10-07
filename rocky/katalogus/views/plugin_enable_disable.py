import structlog
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django.urls.base import reverse
from django.utils.translation import gettext_lazy as _

from katalogus.views.mixins import SinglePluginView

logger = structlog.get_logger(__name__)


class PluginEnableDisableView(SinglePluginView):
    def post(self, request, *args, **kwargs):
        plugin_state = kwargs["plugin_state"]

        if plugin_state == "True":
            logger.info("Disabling plugin", event_code=800022, plugin=self.plugin.name)
            self.katalogus_client.disable_plugin(self.plugin)
            messages.add_message(
                self.request,
                messages.WARNING,
                _("{} '{}' disabled.").format(self.plugin.type.title(), self.plugin.name),
            )
            return HttpResponseRedirect(request.POST.get("current_url"))

        if self.plugin.can_scan(self.organization_member):
            logger.info("Enabling plugin", event_code=800021, plugin=self.plugin.name)
            self.katalogus_client.enable_plugin(self.plugin)
            messages.add_message(
                self.request, messages.SUCCESS, _("{} '{}' enabled.").format(self.plugin.type.title(), self.plugin.name)
            )
        else:
            if (
                self.organization_member.trusted_clearance_level
                != self.organization_member.acknowledged_clearance_level
            ):
                member_clearance_level_text = _(
                    "You have not acknowledged your clearance level. "
                    "Go to your profile page to acknowledge your clearance level."
                )
            elif self.organization_member.max_clearance_level < 0:
                member_clearance_level_text = _(
                    "Your clearance level is not set. Go to your profile page to see your clearance "
                    "or contact the administrator to set a clearance level."
                )
            else:
                clearance_level = self.organization_member.max_clearance_level

                member_clearance_level_text = _(
                    "Your clearance level is L{}. Contact your administrator to get a higher clearance level."
                ).format(clearance_level)

            messages.add_message(
                self.request,
                messages.ERROR,
                _("To enable {} you need at least a clearance level of L{}. " + member_clearance_level_text).format(
                    self.plugin.name.title(), self.plugin.scan_level.value
                ),
            )

        return redirect(reverse("katalogus", kwargs={"organization_code": self.organization.code}))
