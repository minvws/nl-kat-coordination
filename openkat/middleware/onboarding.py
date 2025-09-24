from django.shortcuts import redirect
from django.urls.base import reverse

from onboarding.view_helpers import ONBOARDING_PERMISSIONS
from openkat.models import OrganizationMember


def OnboardingMiddleware(get_response):
    def middleware(request):
        response = get_response(request)

        if not request.user.is_authenticated:
            return response

        # do not redirect itself, otherwise it will end up in endless loop
        skip = any(
            x in request.path
            for x in ["/onboarding/", "/admin/", "/login/", "/two_factor/", "/i18n/", "/introduction/", "/health/"]
        )
        if skip or request.user.onboarded or request.path.startswith("/api/"):
            return response

        request.user.onboarded = True
        request.user.save()

        if request.user.is_superuser:
            return redirect(reverse("step_introduction_registration"))

        if (member := OrganizationMember.objects.filter(user=request.user).first()) and member.has_perms(
            ONBOARDING_PERMISSIONS
        ):
            return redirect(reverse("step_introduction", kwargs={"organization_code": member.organization.code}))

        return response

    return middleware
