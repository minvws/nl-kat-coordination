from pathlib import Path

import sys
from datetime import datetime, timezone
from logging import getLogger
from typing import Optional, List, Dict, Any

from django.contrib.auth import get_user_model
from django.core.management import BaseCommand
from octopoes.connector.octopoes import OctopoesAPIConnector
from octopoes.models import DEFAULT_SCAN_LEVEL_FILTER, DEFAULT_SCAN_PROFILE_TYPE_FILTER
from octopoes.models.ooi.findings import Finding, MutedFinding

from django.conf import settings
from rocky.keiko import keiko_client, ReportsService
from rocky.views.finding_list import generate_findings_metadata
from rocky.views.mixins import OOIList
from tools.models import Organization
from tools.ooi_helpers import RiskLevelSeverity

User = get_user_model()
logger = getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Generates a Finding report for all findings in an organization. "
        "Requires either the id (-i) or the unique code (-c) of an organization."
        "When no output file is specified (-o), you have to pipe the output to a file yourself."
    )

    def add_arguments(self, parser):
        parser.add_argument("--id", "-i", type=int, help="The primary key of the organization.")
        parser.add_argument("--code", "-c", type=str, help="The unique organization code.")
        parser.add_argument(
            "--output",
            "-o",
            type=Path,
            help="Destination path of the report. "
            "When no output file is specified, you have to pipe the output to a file yourself.",
        )
        parser.add_argument(
            "--min-severity",
            "-s",
            type=RiskLevelSeverity,
            default=RiskLevelSeverity.NONE,
            choices=[severity for severity in RiskLevelSeverity],
            help="Only include Findings with at least this severity in the report.",
        )

    def handle(self, *args, **options):
        if not options["output"]:
            if self.stdout.isatty():
                self.stderr.write(
                    "Can't print PDF file directly to stdout. Set a destination path or pipe the output to a file"
                )
                sys.exit(1)

        organization = self.get_organization(**options)

        if not organization:
            self.stderr.write("Provider either a valid primary key of an organization or a valid code (not both)")
            sys.exit(1)

        valid_time = datetime.now(timezone.utc)
        report = ReportsService(keiko_client).get_organization_finding_report(
            valid_time,
            organization.name,
            self.get_findings_metadata(organization, valid_time, options),
        )

        if options["output"]:
            file_path = options["output"]
            file_path.write_bytes(report.read())
            return

        self.stdout.buffer.write(report.read())

    @staticmethod
    def get_findings_metadata(organization, valid_time, options) -> List[Dict[str, Any]]:
        ooi_list = OOIList(
            OctopoesAPIConnector(settings.OCTOPOES_API, organization.code),
            {Finding},
            valid_time,
            scan_level=DEFAULT_SCAN_LEVEL_FILTER,
            scan_profile_type=DEFAULT_SCAN_PROFILE_TYPE_FILTER,
        )
        muted_list = OOIList(
            OctopoesAPIConnector(settings.OCTOPOES_API, organization.code),
            {MutedFinding},
            valid_time,
            scan_level=DEFAULT_SCAN_LEVEL_FILTER,
            scan_profile_type=DEFAULT_SCAN_PROFILE_TYPE_FILTER,
        )
        severities = [item for item in RiskLevelSeverity if item >= options["min_severity"]]

        return generate_findings_metadata(ooi_list, muted_list, severities)

    @staticmethod
    def get_organization(**options) -> Optional[Organization]:
        if options["code"] and options["id"]:
            return None

        if options["code"]:
            return Organization.objects.get(code=options["code"])

        if options["id"]:
            return Organization.objects.get(pk=options["id"])
