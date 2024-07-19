from unittest import TestCase

from boefjes.job_handler import serialize_ooi
from boefjes.plugins.kat_politie_check_tradepartner.normalize import OutdatedPolitieCheck, run
from octopoes.models import Reference
from octopoes.models.ooi.findings import Finding, KATFindingType
from octopoes.models.ooi.network import Network
from octopoes.models.ooi.web import Hostname
from tests.loading import get_dummy_data


class PolitieTradepartnerCheckTest(TestCase):
    def test_normalizer_fraudulent(self):
        """Test if the webpage returning a fraudulent website is marked correctly as fraudulent"""
        input_ooi = Hostname(
            object_type="Hostname",
            primary_key="Hostname|internet|834953-d2.myshopify.com",
            network=Reference("Network|internet"),
            name="834953-d2.myshopify.com",
        )

        output = run(
            serialize_ooi(input_ooi),
            get_dummy_data("raw/politie_tradepartner_check_fraudulent_response.html"),
        )

        findingType: KATFindingType = next(output)
        self.assertTrue(type(findingType) == KATFindingType)

        finding: Finding = next(output)
        self.assertTrue(type(finding), Finding)
        self.assertEqual(finding.finding_type, findingType.reference)

        with self.assertRaises(StopIteration):
            next(output)

    def test_normalizer_innocent(self):
        """Test if the webpage returning an innocent website is marked correctly as innocent"""
        input_ooi = Hostname(
            object_type="Hostname",
            primary_key="Hostname|internet|google.com",
            network=Reference("Network|internet"),
            name="google.com",
        )
        output = run(
            serialize_ooi(input_ooi),
            get_dummy_data("raw/politie_tradepartner_check_innocent_response.html"),
        )

        with self.assertRaises(StopIteration):
            next(output)

    def test_normalizer_broken(self):
        """Test the normalizer returns an exception in case the webpage returned has an unexpected format"""
        input_ooi = Hostname(network=Network(name="internet").reference, name="non-existing-website.com")

        with self.assertRaises(OutdatedPolitieCheck):
            list(run(serialize_ooi(input_ooi), b""))
