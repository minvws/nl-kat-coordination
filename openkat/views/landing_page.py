from django.shortcuts import redirect
from django.views.generic import TemplateView


class LandingPageView(TemplateView):
    template_name = "landing_page.html"

    def get(self, request, *args, **kwargs):
        if self.request.user.is_authenticated:
            return redirect("plugin_list")

        return super().get(request, *args, **kwargs)
