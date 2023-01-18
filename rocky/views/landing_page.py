from django.shortcuts import redirect
from django.views.generic import TemplateView


class LandingPageView(TemplateView):
    template_name = "landing_page.html"

    def get(self, request, *args, **kwargs):
        if self.request.user.is_authenticated:
            return redirect("crisis_room")

        return super().get(request, *args, **kwargs)
