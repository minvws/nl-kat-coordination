from unittest import TestCase

from octopoes.models.types import (
    CVEFindingType,
    Finding,
    Software,
)
from octopoes.models.ooi.findings import SnykFindingType

from boefjes.plugins.kat_snyk.normalize import run
from boefjes.job_models import NormalizerMeta
from tests.stubs import get_dummy_data


class DnsTest(TestCase):
    maxDiff = None

    def test_snyk_no_findings(self):
        meta = NormalizerMeta.parse_raw(get_dummy_data("snyk-normalizer.json"))

        oois = list(
            run(
                meta,
                get_dummy_data("inputs/snyk-result-no-findings.json"),
            )
        )

        # noinspection PyTypeChecker
        expected = ()

        self.assertCountEqual(expected, oois)

    def test_snyk_findings(self):
        meta = NormalizerMeta.parse_raw(get_dummy_data("snyk-normalizer.json"))

        oois = list(
            run(
                meta,
                get_dummy_data("inputs/snyk-result-findings.json"),
            )
        )

        software = Software(name="lodash", version="1.1.0")

        snyk_finding_data = [
            ("SNYK-JS-LODASH-590103", "Prototype Pollution"),
            ("SNYK-JS-LODASH-608086", "Prototype Pollution"),
        ]
        cve_finding_data = [
            ("CVE-2018-16487", "Prototype Pollution"),
            ("CVE-2018-3721", "Prototype Pollution"),
            ("CVE-2019-1010266", "Regular Expression Denial of Service (ReDoS)"),
            ("CVE-2019-10744", "Prototype Pollution"),
            ("CVE-2020-28500", "Regular Expression Denial of Service (ReDoS)"),
            ("CVE-2020-8203", "Prototype Pollution"),
            ("CVE-2021-23337", "Command Injection"),
        ]

        snyk_findingtypes = []
        snyk_findings = []
        cve_findingtypes = []
        cve_findings = []

        for finding in snyk_finding_data:
            snyk_ft = SnykFindingType(id=finding[0])
            snyk_findingtypes.append(snyk_ft)
            snyk_findings.append(
                Finding(
                    finding_type=snyk_ft.reference,
                    ooi=software.reference,
                    description=finding[1],
                )
            )

        for finding in cve_finding_data:
            cve_ft = CVEFindingType(id=finding[0])
            cve_findingtypes.append(cve_ft)
            cve_findings.append(
                Finding(
                    finding_type=cve_ft.reference,
                    ooi=software.reference,
                    description=finding[1],
                )
            )

        # noinspection PyTypeChecker
        expected = snyk_findingtypes + snyk_findings + cve_findingtypes + cve_findings

        self.assertCountEqual(expected, oois)
