import json
from unittest import TestCase, mock

from boefjes.job_models import BoefjeMeta, NormalizerMeta
from boefjes.plugins.kat_snyk.main import run as run_boefje
from boefjes.plugins.kat_snyk.normalize import run
from octopoes.models.ooi.findings import SnykFindingType
from octopoes.models.types import (
    CVEFindingType,
    Finding,
    Software,
)
from tests.loading import get_dummy_data


class SnykTest(TestCase):
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

    @mock.patch("boefjes.plugins.kat_snyk.main.requests.get")
    def test_snyk_html_parser(self, mock_get):
        boefje_meta = BoefjeMeta.parse_raw(get_dummy_data("snyk-job.json"))

        # Mock the first GET request
        mock_first_get = mock.Mock()
        mock_first_get.content = get_dummy_data("snyk-vuln.html")

        # Mock the next GET request
        mock_second_get = mock.Mock()
        mock_second_get.content = get_dummy_data("snyk-vuln2.html")

        # Mock the next 7 GET requests
        mock_third_get = mock.Mock()
        mock_third_get.content = get_dummy_data("snyk-vuln3.html")

        mock_get.side_effect = [mock_first_get] + [mock_second_get] + [mock_third_get] * 7

        mime_types, result = run_boefje(boefje_meta)[0]

        output = json.loads(result)

        self.assertListEqual(output["table_versions"], [])
        self.assertListEqual(
            output["table_vulnerabilities"],
            [
                {
                    "Vuln_href": "SNYK-JS-LODASH-1018905",
                    "Vuln_text": "Regular Expression Denial of Service (ReDoS)",
                    "Vuln_versions": "<4.17.21",
                },
                {"Vuln_href": "SNYK-JS-LODASH-608086", "Vuln_text": "Prototype Pollution", "Vuln_versions": "<4.17.17"},
                {"Vuln_href": "SNYK-JS-LODASH-450202", "Vuln_text": "Prototype Pollution", "Vuln_versions": "<4.17.12"},
                {
                    "Vuln_href": "SNYK-JS-LODASH-73639",
                    "Vuln_text": "Regular Expression Denial of Service (ReDoS)",
                    "Vuln_versions": "<4.17.11",
                },
                {"Vuln_href": "SNYK-JS-LODASH-73638", "Vuln_text": "Prototype Pollution", "Vuln_versions": "<4.17.11"},
                {"Vuln_href": "npm:lodash:20180130", "Vuln_text": "Prototype Pollution", "Vuln_versions": "<4.17.5"},
            ],
        )
        self.assertListEqual(
            output["cve_vulnerabilities"], [{"cve_code": "CVE-2021-23337", "Vuln_text": "Command Injection"}]
        )
