from django.urls import path

from katalogus import views
from katalogus.views.change_clearance_level import ChangeClearanceLevel
from katalogus.views.plugin_detail import PluginDetailView, PluginCoverImgView
from katalogus.views.plugin_settings_add import PluginSingleSettingAddView, PluginSettingsAddView
from katalogus.views.plugin_settings_delete import PluginSettingsDeleteView
from katalogus.views.plugin_settings_edit import PluginSettingsUpdateView

urlpatterns = [
    path("", views.KATalogusView.as_view(), name="katalogus"),
    path("view/<view>/", views.KATalogusView.as_view(), name="katalogus"),
    path(
        "settings/",
        views.KATalogusSettingsListView.as_view(),
        name="katalogus_settings",
    ),
    path(
        "plugins/<plugin_type>/<plugin_id>/",
        PluginDetailView.as_view(),
        name="plugin_detail",
    ),
    path(
        "plugins/<plugin_type>/<plugin_id>/<plugin_state>/",
        views.PluginEnableDisableView.as_view(),
        name="plugin_enable_disable",
    ),
    path(
        "plugins/<plugin_id>/cover.jpg",
        PluginCoverImgView.as_view(),
        name="plugin_cover",
    ),
    path(
        "plugins/<plugin_type>/<plugin_id>/settings/add/",
        PluginSettingsAddView.as_view(),
        name="plugin_settings_add",
    ),
    path(
        "plugins/<plugin_type>/<plugin_id>/change-clearance-level/<scan_level>/",
        ChangeClearanceLevel.as_view(),
        name="change_clearance_level",
    ),
    path(
        "plugins/<plugin_type>/<plugin_id>/settings/add/<setting_name>/",
        PluginSingleSettingAddView.as_view(),
        name="plugin_settings_add_single",
    ),
    path(
        "plugins/<plugin_type>/<plugin_id>/settings/edit/<setting_name>/",
        PluginSettingsUpdateView.as_view(),
        name="plugin_settings_edit",
    ),
    path(
        "plugins/<plugin_type>/<plugin_id>/settings/delete/<name>/",
        PluginSettingsDeleteView.as_view(),
        name="plugin_settings_delete",
    ),
]
