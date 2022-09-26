from django.views.generic import FormView, ListView, TemplateView
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django_otp.decorators import otp_required
from two_factor.views.utils import class_view_decorator
from katalogus.client import get_katalogus
from katalogus.forms import PluginSettingsAddForm, PluginSettingsEditForm
from django.contrib.auth.mixins import PermissionRequiredMixin


@class_view_decorator(otp_required)
class PluginSettingsListView(PermissionRequiredMixin, ListView):
    """View that gives an overview of all general settings for plugins in KAT-alogus"""

    template_name = "plugin_settings.html"
    paginate_by = 10
    permission_required = "tools.can_scan_organization"
    plugin_type = "boefjes"

    def dispatch(self, request, *args, **kwargs):
        self.plugin_id = kwargs["plugin_id"]
        self.katalogus_client = get_katalogus(
            request.user.organizationmember.organization.code
        )
        return super().dispatch(request, *args, **kwargs)

    def get_plugin_name(self):
        return self.katalogus_client.get_boefje(self.plugin_id).name

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [
            {"url": reverse("katalogus"), "text": _("KAT-alogus")},
            {
                "url": reverse("katalogus_detail", kwargs={"id": self.plugin_id}),
                "text": self.get_plugin_name(),
            },
            {
                "url": reverse(
                    "plugin_settings_list",
                    kwargs={
                        "plugin_type": self.plugin_type,
                        "plugin_id": self.plugin_id,
                    },
                ),
                "text": _("Settings"),
            },
        ]
        context["plugin_id"] = self.plugin_id
        context["plugin_type"] = self.plugin_type
        context["plugin_name"] = self.get_plugin_name()
        return context

    def get_queryset(self):
        settings = self.katalogus_client.get_plugin_settings(plugin_id=self.plugin_id)
        queryset = [{name: value} for name, value in settings.items()]
        queryset.reverse()
        return queryset


@class_view_decorator(otp_required)
class PluginSettingsAddView(PermissionRequiredMixin, FormView):
    """View to add a general setting for all plugins in KAT-alogus"""

    form_class = PluginSettingsAddForm
    template_name = "plugin_settings_add.html"
    permission_required = "tools.can_scan_organization"
    plugin_type = "boefjes"

    def dispatch(self, request, *args, **kwargs):
        self.plugin_id = kwargs["plugin_id"]
        self.katalogus_client = get_katalogus(
            request.user.organizationmember.organization.code
        )
        self.plugin_name = self.katalogus_client.get_boefje(self.plugin_id).name
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [
            {"url": reverse("katalogus"), "text": _("KAT-alogus")},
            {
                "url": reverse("katalogus_detail", kwargs={"id": self.plugin_id}),
                "text": self.plugin_name,
            },
            {
                "url": reverse(
                    "plugin_settings_list",
                    kwargs={
                        "plugin_type": self.plugin_type,
                        "plugin_id": self.plugin_id,
                    },
                ),
                "text": _("Settings"),
            },
            {
                "url": reverse(
                    "plugin_settings_add",
                    kwargs={
                        "plugin_type": self.plugin_type,
                        "plugin_id": self.plugin_id,
                    },
                ),
                "text": _("Add"),
            },
        ]
        context["plugin_id"] = self.plugin_id
        context["plugin_type"] = self.plugin_type
        context["plugin_name"] = self.plugin_name
        return context

    def is_name_duplicate(self, name):
        setting = self.katalogus_client.get_plugin_setting(self.plugin_id, key=name)
        return "message" not in setting

    def get_success_url(self):
        return reverse(
            "plugin_settings_list",
            kwargs={"plugin_type": self.plugin_type, "plugin_id": self.plugin_id},
        )

    def form_valid(self, form):
        name = form.cleaned_data["name"]
        value = form.cleaned_data["value"]
        if self.is_name_duplicate(name):
            self.add_error_notification(
                _("This setting already exists. Use the edit link.")
            )
        else:
            self.katalogus_client.add_plugin_setting(self.plugin_id, name, value)
            self.add_success_notification()

        return super().form_valid(form)

    def add_success_notification(self):
        success_message = _("Setting succesfully added for: ") + self.plugin_name
        messages.add_message(self.request, messages.SUCCESS, success_message)

    def add_error_notification(self, message):
        messages.add_message(self.request, messages.ERROR, message)


@class_view_decorator(otp_required)
class PluginSettingsUpdateView(PermissionRequiredMixin, FormView):
    """View to update/edit a plugin setting for all plugins in KAT-alogus"""

    form_class = PluginSettingsEditForm
    template_name = "plugin_settings_edit.html"
    permission_required = "tools.can_scan_organization"
    plugin_type = "boefjes"

    def dispatch(self, request, *args, **kwargs):
        self.plugin_id = kwargs["plugin_id"]
        self.name = kwargs["name"]

        self.katalogus_client = get_katalogus(
            request.user.organizationmember.organization.code
        )
        if self.key_already_exists(request):
            messages.add_message(
                request,
                messages.ERROR,
                _("The setting you are trying to edit does not exist."),
            )
            return HttpResponseRedirect(
                reverse(
                    "plugin_settings_list",
                    kwargs={
                        "plugin_type": self.plugin_type,
                        "plugin_id": self.plugin_id,
                    },
                )
            )
        self.plugin_name = self.katalogus_client.get_boefje(self.plugin_id).name
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        initial = super().get_initial()
        initial["value"] = self.katalogus_client.get_plugin_setting(
            plugin_id=self.plugin_id, key=self.name
        )
        return initial

    def key_already_exists(self, request):
        setting = self.katalogus_client.get_plugin_setting(
            self.plugin_id, key=self.name
        )
        return "message" in setting

    def get_success_url(self):
        return reverse(
            "plugin_settings_list",
            kwargs={"plugin_type": self.plugin_type, "plugin_id": self.plugin_id},
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [
            {"url": reverse("katalogus"), "text": _("KAT-alogus")},
            {
                "url": reverse("katalogus_detail", kwargs={"id": self.plugin_id}),
                "text": self.plugin_name,
            },
            {
                "url": reverse(
                    "plugin_settings_list",
                    kwargs={
                        "plugin_type": self.plugin_type,
                        "plugin_id": self.plugin_id,
                    },
                ),
                "text": _("Settings"),
            },
            {
                "url": reverse(
                    "plugin_settings_add",
                    kwargs={
                        "plugin_type": self.plugin_type,
                        "plugin_id": self.plugin_id,
                    },
                ),
                "text": _("Edit"),
            },
        ]
        context["name"] = self.name
        context["plugin_id"] = self.plugin_id
        context["plugin_type"] = self.plugin_type
        context["plugin_name"] = self.plugin_name
        return context

    def form_valid(self, form):
        value = form.cleaned_data["value"]
        self.katalogus_client.update_plugin_setting(
            plugin_id=self.plugin_id, name=self.name, value=value
        )
        messages.add_message(
            self.request, messages.SUCCESS, _("Setting succesfully updated.")
        )
        return super().form_valid(form)


@class_view_decorator(otp_required)
class PluginSettingsDeleteView(PermissionRequiredMixin, TemplateView):
    template_name = "plugin_settings_delete.html"
    permission_required = "tools.can_scan_organization"
    plugin_type = "boefjes"

    def dispatch(self, request, *args, **kwargs):
        self.plugin_id = kwargs["plugin_id"]
        self.name = kwargs["name"]
        self.katalogus_client = get_katalogus(
            request.user.organizationmember.organization.code
        )
        self.plugin_name = self.katalogus_client.get_boefje(self.plugin_id).name

        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self.delete(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [
            {"url": reverse("katalogus"), "text": _("KAT-alogus")},
            {
                "url": reverse("katalogus_detail", kwargs={"id": self.plugin_id}),
                "text": self.plugin_name,
            },
            {
                "url": reverse(
                    "plugin_settings_list",
                    kwargs={
                        "plugin_type": self.plugin_type,
                        "plugin_id": self.plugin_id,
                    },
                ),
                "text": _("Settings"),
            },
            {
                "url": reverse(
                    "plugin_settings_add",
                    kwargs={
                        "plugin_type": self.plugin_type,
                        "plugin_id": self.plugin_id,
                    },
                ),
                "text": _("Add"),
            },
        ]
        context["name"] = self.name
        context["plugin_id"] = self.plugin_id
        context["plugin_type"] = self.plugin_type
        context["plugin_name"] = self.plugin_name
        context["cancel_url"] = self.get_success_url()
        return context

    def get_success_url(self):
        return reverse(
            "plugin_settings_list",
            kwargs={"plugin_type": self.plugin_type, "plugin_id": self.plugin_id},
        )

    def delete(self, request, *args, **kwargs):
        self.katalogus_client.delete_plugin_setting(
            plugin_id=self.plugin_id, name=self.name
        )
        messages.add_message(
            request,
            messages.SUCCESS,
            _("Setting {} for plugin {} succesfully deleted.").format(
                self.name, self.plugin_name
            ),
        )
        return HttpResponseRedirect(self.get_success_url())
