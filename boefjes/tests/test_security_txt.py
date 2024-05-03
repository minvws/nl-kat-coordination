from unittest import TestCase

from boefjes.job_models import NormalizerMeta
from boefjes.plugins.kat_security_txt_downloader.normalize import run
from octopoes.models import Reference
from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.ooi.network import IPAddressV4, IPPort, Network
from octopoes.models.ooi.service import IPService, Service
from octopoes.models.ooi.web import URL, SecurityTXT, Website
from octopoes.models.types import Finding, KATFindingType
from tests.loading import get_dummy_data


class SecurityTXTTest(TestCase):
    maxDiff = None

    def test_security_txt_same_website(self):
        meta = NormalizerMeta.model_validate_json(get_dummy_data("security-txt-normalizer.json"))

        oois = list(
            run(
                meta,
                get_dummy_data("inputs/security_txt_result_same_website.json"),
            )
        )

        expected = []
        url = URL(raw="https://example.com/.well-known/security.txt", network=Network(name="internet").reference)
        expected.append(url)
        expected.append(
            SecurityTXT(
                website=Reference.from_str("Website|internet|1.1.1.1|tcp|443|https|internet|example.com"),
                url=url.reference,
                security_txt="This is the content",
                redirects_to=None,
            )
        )

        self.assertEqual(expected, oois)

    def test_security_txt_different_website(self):
        meta = NormalizerMeta.model_validate_json(get_dummy_data("security-txt-normalizer.json"))

        oois = list(
            run(
                meta,
                get_dummy_data("inputs/security_txt_result_different_website.json"),
            )
        )

        expected = []
        url_original = URL(
            raw="https://example.com/.well-known/security.txt", network=Network(name="internet").reference
        )
        expected.append(url_original)
        url = URL(raw="https://www.example.com/.well-known/security.txt", network=Network(name="internet").reference)
        expected.append(url)
        expected.append(Hostname(name="www.example.com", network=Network(name="internet").reference))
        ip = IPAddressV4(address="192.0.2.1", network=Network(name="internet").reference)
        expected.append(ip)
        expected.append(Service(name="https"))
        port = IPPort(address=ip.reference, port=443, protocol="tcp")
        expected.append(port)
        ip_service = IPService(ip_port=port.reference, service=Service(name="https").reference)
        expected.append(ip_service)
        website = Website(
            ip_service=ip_service.reference,
            hostname=Hostname(name="www.example.com", network=Network(name="internet").reference).reference,
        )
        expected.append(website)
        security_txt = SecurityTXT(
            website=website.reference, url=url.reference, security_txt="This is the content", redirects_to=None
        )
        expected.append(security_txt)
        expected.append(
            SecurityTXT(
                website=Reference.from_str("Website|internet|192.0.2.0|tcp|443|https|internet|example.com"),
                url=url_original.reference,
                security_txt=None,
                redirects_to=security_txt.reference,
            )
        )
        self.assertEqual(expected, oois)

    def test_security_txt_legacy_only(self):
        meta = NormalizerMeta.model_validate_json(get_dummy_data("security-txt-normalizer.json"))

        oois = list(
            run(
                meta,
                get_dummy_data("inputs/security_txt_results_legacy_only.json"),
            )
        )

        expected = []
        url = URL(raw="https://example.com/security.txt", network=Network(name="internet").reference)
        expected.append(url)
        content = "Contact: mailto:security@example.com\nPreferred-Languages: nl, en\nExpires: 2030-01-01T00:00:00.000Z"
        expected.append(
            SecurityTXT(
                website=Reference.from_str("Website|internet|1.1.1.1|tcp|443|https|internet|www.example.com"),
                url=url.reference,
                security_txt=content,
                redirects_to=None,
            )
        )

        ft = KATFindingType(id="KAT-LEGACY-SECURITY-LOCATION")
        expected.append(ft)
        expected.append(
            Finding(
                description="Only legacy /security.txt location found.",
                finding_type=ft.reference,
                ooi=Reference.from_str("Website|internet|1.1.1.1|tcp|443|https|internet|www.example.com")
            )
        )

        self.assertEqual(expected, oois)
