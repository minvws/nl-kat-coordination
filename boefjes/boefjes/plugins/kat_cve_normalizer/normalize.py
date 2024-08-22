import re
from collections.abc import Iterable

from boefjes.job_models import NormalizerOutput
from octopoes.models import Reference
from octopoes.models.ooi.findings import CVEFindingType, Finding, KATFindingType, RetireJSFindingType, SnykFindingType


def run(input_ooi: dict, raw: bytes) -> Iterable[NormalizerOutput]:
    ooi = Reference.from_str(input_ooi["primary_key"])
    finding_ids_str = raw.decode()
    finding_ids_list = [fid.strip().upper() for fid in finding_ids_str.split(",")]

    # Validating CVE format (e.g., CVE-YYYY-NNNNN)
    cve_pattern = re.compile(r"CVE-\d{4}-\d{4,7}")

    finding_type_mapping = {
        "CVE-": CVEFindingType,
        "KAT-": KATFindingType,
        "SNYK-": SnykFindingType,
        "RETIREJS-": RetireJSFindingType,
    }

    for finding_id in finding_ids_list:
        if finding_id.startswith("CVE-") and not cve_pattern.match(finding_id):
            continue  # skip incorrect cves

        for prefix, FindingTypeClass in finding_type_mapping.items():
            if finding_id.startswith(prefix):
                finding_type = FindingTypeClass(id=finding_id)
                finding = Finding(
                    finding_type=finding_type.reference,
                    ooi=ooi,
                    description=f"{finding_id} is found on this OOI",
                )
                yield finding_type
                yield finding
                break
