from django.urls import path

from katalogus.views.change_clearance_level import ChangeClearanceLevel
from katalogus.views.katalogus import KATalogusView
from katalogus.views.katalogus_settings import ConfirmCloneSettingsView, KATalogusSettingsView
from katalogus.views.plugin_detail import PluginCoverImgView, PluginDetailView
from katalogus.views.plugin_enable_disable import PluginEnableDisableView
from katalogus.views.plugin_settings_add import PluginSettingsAddView
from katalogus.views.plugin_settings_delete import PluginSettingsDeleteView

urlpatterns = [
    path("", KATalogusView.as_view(), name="katalogus"),
    path("view/<view>/", KATalogusView.as_view(), name="katalogus"),
    path(
        "settings/",
        KATalogusSettingsView.as_view(),
        name="katalogus_settings",
    ),
    path(
        "settings/migrate/",
        KATalogusSettingsView.as_view(),
        name="katalogus_clone_settings",
    ),
    path(
        "settings/migrate/confirmation/<to_organization>/",
        ConfirmCloneSettingsView.as_view(),
        name="confirm_clone_settings",
    ),
    path(
        "plugins/<plugin_type>/<plugin_id>/",
        PluginDetailView.as_view(),
        name="plugin_detail",
    ),
    path(
        "plugins/<plugin_type>/<plugin_id>/<plugin_state>/",
        PluginEnableDisableView.as_view(),
        name="plugin_enable_disable",
    ),
    path(
        "plugins/<plugin_id>/cover.jpg",
        PluginCoverImgView.as_view(),
        name="plugin_cover",
    ),
    path(
        "plugins/<plugin_type>/<plugin_id>/change-clearance-level/<scan_level>/",
        ChangeClearanceLevel.as_view(),
        name="change_clearance_level",
    ),
    path(
        "plugins/<plugin_type>/<plugin_id>/settings/add/",
        PluginSettingsAddView.as_view(),
        name="plugin_settings_add",
    ),
    path(
        "plugins/<plugin_type>/<plugin_id>/settings/delete/",
        PluginSettingsDeleteView.as_view(),
        name="plugin_settings_delete",
    ),
]
