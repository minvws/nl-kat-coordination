from django.shortcuts import redirect
from django.views.generic import TemplateView


class LandingPageView(TemplateView):
    template_name = "landing_page.html"

    def get(self, request, *args, **kwargs):
        if self.request.user.is_authenticated:
            if not self.request.user.organizationmember.onboarded:
                return redirect("onboarding_index")
            else:
                return redirect("crisis_room")

        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["breadcrumbs"] = []

        return context
