from django.shortcuts import redirect
from django.urls.base import reverse
from tools.models import OrganizationMember
from tools.user_helpers import is_red_team


def OnboardingMiddleware(get_response):
    def middleware(request):
        response = get_response(request)
        if request.user.is_authenticated:
            member_onboarded = OrganizationMember.objects.filter(
                user=request.user, onboarded=True
            )
            # do not redirect itself, otherwise it will endup in endless loop
            # with too many redirects
            # exclude admin urls
            if not (
                "/onboarding/" in request.path
                or "/admin/" in request.path
                or "/login/" in request.path
                or "/two_factor/" in request.path
                or "/plugins" in request.path
                or "/i18n/" in request.path
                or "/introduction/" in request.path
            ):
                if not member_onboarded:
                    if request.user.is_superuser:
                        return redirect(reverse("step_introduction_registration"))
                    if is_red_team(request.user):
                        return redirect(reverse("step_introduction"))
        return response

    return middleware
