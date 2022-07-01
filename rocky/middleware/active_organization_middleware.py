from octopoes.connector.octopoes import OctopoesAPIConnector

from rocky.settings import OCTOPOES_API
from tools.models import Organization
from tools.user_helpers import can_switch_organization

from logging import getLogger

logger = getLogger(__name__)


def ActiveOrganizationMiddleware(get_response):
    def middleware(request):

        active_organization = None
        if request.user is not None:

            if request.user.has_perm("tools.can_switch_organization"):
                # Try to fetch from session
                session_active_org_id = request.session.get("active_organization_id")
                if session_active_org_id is not None:
                    active_organization = Organization.objects.get(
                        pk=session_active_org_id
                    )

                # Otherwise first object
                if active_organization is None:
                    active_organization = Organization.objects.first()

                # Set session
                if active_organization is not None:
                    request.session["active_organization_id"] = active_organization.id

            # Non red-teamer only if the user is connected to an organisation
            elif (
                getattr(request.user, "organizationmember", None) is not None
                and getattr(request.user.organizationmember, "organization", None)
                is not None
            ):
                active_organization = request.user.organizationmember.organization
                request.session["active_organization_id"] = active_organization.id

        request.active_organization = active_organization
        response = get_response(request)
        return response

    return middleware


def OctopoesConnectorMiddleware(get_response):
    def middleware(request):

        # Create an Octopoes API Connector if possible
        octopoes_api_connector = None

        if (
            getattr(request, "active_organization", None) is not None
            and request.active_organization.code
        ):
            code = request.active_organization.code
            octopoes_api_connector = OctopoesAPIConnector(
                base_uri=OCTOPOES_API, client=code
            )

        request.octopoes_api_connector = octopoes_api_connector
        response = get_response(request)
        return response

    return middleware
