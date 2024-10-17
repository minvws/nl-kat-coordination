from account.mixins import OrganizationAPIMixin
from django.http import HttpResponseRedirect
from django.urls import reverse
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from structlog import get_logger
from tools.view_helpers import url_with_querystring

from octopoes.models import Reference
from reports.serializers import ReportSerializer
from rocky.views.mixins import ReportList

logger = get_logger(__name__)


class ReportViewSet(OrganizationAPIMixin, viewsets.ModelViewSet):
    # There are no extra permissions needed to view reports, so IsAuthenticated is enough for list/retrieve
    permission_classes = [IsAuthenticated]
    serializer_class = ReportSerializer

    def get_queryset(self):
        return ReportList(self.octopoes_api_connector, self.valid_time)

    def get_object(self):
        pk = self.kwargs["pk"]

        return self.octopoes_api_connector.get(Reference.from_str(f"Report|{pk}"), valid_time=self.valid_time)

    @action(detail=True)
    def pdf(self, request, pk):
        report_ooi_id = f"Report|{pk}"

        url = url_with_querystring(
            reverse("view_report_pdf", kwargs={"organization_code": self.organization.code}),
            True,
            report_id=report_ooi_id,
            observed_at=self.valid_time.isoformat(),
        )

        return HttpResponseRedirect(redirect_to=url)
