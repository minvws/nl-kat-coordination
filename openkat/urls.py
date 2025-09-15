from django.contrib import admin
from django.contrib.auth.views import LogoutView
from django.urls import include, path
from two_factor.urls import urlpatterns as tf_urls  # type: ignore[import-not-found]

urlpatterns = [
    path("", include(tf_urls)),
    path("account/logout/", LogoutView.as_view(), name="logout"),
    path("admin/", admin.site.urls),
    path("ooi/", include("ooi.urls")),
]
