from django.urls import path
from katalogus import views
from rocky.views import (
    BoefjeDetailView,
    BoefjeConsumableObjectType,
    BoefjeConsumableObjectAddView,
    KATalogusListView,
)

urlpatterns = [
    path("", KATalogusListView.as_view(), name="katalogus"),
    path(
        "settings/",
        views.KATalogusSettingsListView.as_view(),
        name="katalogus_settings",
    ),
    path(
        "plugins/boefjes/<id>/",
        BoefjeDetailView.as_view(),
        name="katalogus_detail",
    ),
    path(
        "plugins/<plugin_type>/<plugin_id>/settings/",
        views.PluginSettingsListView.as_view(),
        name="plugin_settings_list",
    ),
    path(
        "plugins/<plugin_type>/<plugin_id>/settings/add/",
        views.PluginSettingsAddView.as_view(),
        name="plugin_settings_add",
    ),
    path(
        "plugins/<plugin_type>/<plugin_id>/settings/edit/<name>/",
        views.PluginSettingsUpdateView.as_view(),
        name="plugin_settings_edit",
    ),
    path(
        "plugins/<plugin_type>/<plugin_id>/settings/delete/<name>/",
        views.PluginSettingsDeleteView.as_view(),
        name="plugin_settings_delete",
    ),
    path(
        "kat-alogus/<id>/add-consumable-object/",
        BoefjeConsumableObjectType.as_view(),
        name="boefje_add_consumable_type",
    ),
    path(
        "kat-alogus/<id>/add-consumable-object/<add_ooi_type>/",
        BoefjeConsumableObjectAddView.as_view(),
        name="boefje_add_consumable_object",
    ),
]
