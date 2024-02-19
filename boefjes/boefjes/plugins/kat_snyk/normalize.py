import json
import logging
from collections.abc import Iterable

from boefjes.job_models import NormalizerMeta
from boefjes.plugins.kat_snyk import check_version
from octopoes.models import OOI, Reference
from octopoes.models.ooi.findings import (
    CVEFindingType,
    Finding,
    KATFindingType,
    SnykFindingType,
)

logger = logging.getLogger(__name__)


def run(normalizer_meta: NormalizerMeta, raw: bytes | str) -> Iterable[OOI]:
    results = json.loads(raw)
    boefje_meta = normalizer_meta.raw_data.boefje_meta

    pk_ooi = Reference.from_str(boefje_meta.input_ooi)
    input_ = boefje_meta.arguments["input"]["software"]
    software_name = input_["name"]
    software_version = input_["version"]

    if not results["table_versions"] and not results["table_vulnerabilities"] and not results["cve_vulnerabilities"]:
        logger.warning("Couldn't find software %s in the SNYK vulnerability database", software_name)
        return
    elif not results["table_vulnerabilities"] and not results["cve_vulnerabilities"]:
        # no vulnerabilities found
        return
    else:
        for vuln in results["table_vulnerabilities"]:
            snyk_ft = SnykFindingType(id=vuln.get("Vuln_href"))
            yield snyk_ft
            yield Finding(
                finding_type=snyk_ft.reference,
                ooi=pk_ooi,
                description=vuln.get("Vuln_text"),
            )
        for vuln in results["cve_vulnerabilities"]:
            cve_ft = CVEFindingType(id=vuln.get("cve_code"))
            yield cve_ft
            yield Finding(
                finding_type=cve_ft.reference,
                ooi=pk_ooi,
                description=vuln.get("Vuln_text"),
            )

    # Check for latest version
    latest_version = ""
    for version in results["table_versions"]:
        if version.get("is_latest"):
            latest_version = version.get("Version_text")

    if software_version and latest_version and check_version.check_version_in(software_version, f"<{latest_version}"):
        kat_ooi = KATFindingType(id="KAT-SOFTWARE-UPDATE-AVAILABLE")
        yield kat_ooi
        yield Finding(
            finding_type=kat_ooi.reference,
            ooi=pk_ooi,
            description=f"You may want to update to the newest version. Your current version is {software_version} "
            f"while the latest version is {latest_version}",
        )
