from django.shortcuts import redirect
from django.urls.base import reverse
from tools.models import OrganizationMember


def OnboardingMiddleware(get_response):
    def middleware(request):
        response = get_response(request)
        if request.user.is_authenticated:
            member_onboarded = list(filter(lambda o: o.onboarded, request.user.organization_members))

            # do not redirect itself, otherwise it will endup in endless loop
            # with too many redirects
            # exclude admin urls
            if (
                not (
                    "/onboarding/" in request.path
                    or "/admin/" in request.path
                    or "/login/" in request.path
                    or "/two_factor/" in request.path
                    or "/plugins" in request.path
                    or "/i18n/" in request.path
                    or "/introduction/" in request.path
                    or request.path.startswith("/api/")
                )
                and not member_onboarded
            ):
                if request.user.is_superuser and not member_onboarded:
                    return redirect(reverse("step_introduction_registration"))

                if not member_onboarded:
                    member = OrganizationMember.objects.filter(user=request.user)

                    # There might be redteamers without an organization after an organization is deleted.
                    if member.exists() and member.first().is_redteam:
                        # a redteamer can be in many organizations, but we onboard the first one.
                        return redirect(
                            reverse("step_introduction", kwargs={"organization_code": member.first().organization.code})
                        )

        return response

    return middleware
