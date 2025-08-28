from django.urls import path

from plugins.views import (
    EnabledPluginUpdateView,
    EnabledPluginView,
    PluginCoverImageView,
    PluginDetailView,
    PluginListView,
)

urlpatterns = [
    path("plugins/", PluginListView.as_view(), name="plugin_list"),
    path("plugins/<slug:pk>/", PluginDetailView.as_view(), name="plugin_detail"),
    path("plugins/<slug:plugin_id>/cover-image", PluginCoverImageView.as_view(), name="plugin_cover_image"),
    path("enabled-plugin/", EnabledPluginView.as_view(), name="plugin_enabled"),
    path("enabled-plugin/<slug:pk>/", EnabledPluginUpdateView.as_view(), name="edit_enabled_plugin"),
]
