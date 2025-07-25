from django.urls import path

from plugins.views import (
    EnabledPluginUpdateView,
    EnabledPluginView,
    PluginCoverImageView,
    PluginDetailView,
    PluginListView,
)

urlpatterns = [
    path("", PluginListView.as_view(), name="plugin_list"),
    path("<slug:pk>/", PluginDetailView.as_view(), name="plugin_detail"),
    path("<slug:plugin_id>/cover-image", PluginCoverImageView.as_view(), name="plugin_cover_image"),
    path("enabled-plugin", EnabledPluginView.as_view(), name="plugin_enabled"),
    path("enabled-plugin/<slug:pk>", EnabledPluginUpdateView.as_view(), name="edit_plugin_enabled"),
]
