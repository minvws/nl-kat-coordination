import json
from collections.abc import Iterable
from typing import Any

import structlog

from octopoes.models import OOI, Reference
from octopoes.models.ooi.findings import Finding, KATFindingType

REPORT_CATEGORIES_PATH = "boefjes/plugins/kat_abuseipdb/abuseipdb_report_categories.json"

with open(REPORT_CATEGORIES_PATH) as json_file:
    report_categories = json.load(json_file)

logger = structlog.get_logger(__name__)


def run(input_ooi: dict, raw: bytes) -> Iterable[OOI]:
    """Normalize AbuseIPDB output."""
    result = json.loads(raw)
    input_ooi_reference = Reference.from_str(input_ooi["primary_key"])

    if not result:
        logger.info("No AbuseIPDB results available for normalization.")
    elif "data" in result:
        data: dict[str, Any] = result["data"]
        reportcount = int(data.get("totalReports", 0))
        if reportcount > 0:
            confidence = str(data.get("abuseConfidenceScore", "Unknown"))
            reportdate = str(data.get("lastReportedAt", "Unknown"))
            ft = KATFindingType(id="KAT-ABUSE-REPORTS-DETECTED")
            finding = Finding(
                finding_type=ft.reference,
                ooi=input_ooi_reference,
                description=(
                    f"IP {input_ooi_reference.human_readable} is listed {reportcount} times "
                    f"for abuse at AbuseIPDB.com, last reported at: {reportdate} with a "
                    f"confidence of: {confidence}."
                ),
            )
            yield ft
            yield finding

            # Get more detailed findings using the report categories
            # Each report has a list of categories that the report reports see @ammar92
            for report in data.get("reports", []):
                for category in report.get("categories", []):
                    report_info = report_categories.get(str(category), None)
                    if report_info:
                        ft = KATFindingType(
                            id="AbuseIPDB-REPORT",
                            recommendation="Make sure to check out https://www.abuseipdb.com/categories",
                            source="https://www.abuseipdb.com",
                        )
                        finding = Finding(
                            finding_type=ft.reference,
                            ooi=input_ooi_reference,
                            description=f"{report_info['title']} — {report_info['description']}",
                        )
                        yield ft
                        yield finding
