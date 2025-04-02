from unittest import TestCase

from boefjes.plugins.kat_nikto.normalize import run
from octopoes.models import Reference
from octopoes.models.ooi.findings import KATFindingType
from octopoes.models.ooi.software import Software, SoftwareInstance
from octopoes.models.types import Finding
from tests.loading import get_dummy_data


class CVETest(TestCase):
    def test_outdated_found(self):
        input_ooi = {"primary_key": "Hostname|internet|example.com"}
        ooi_ref = Reference.from_str(input_ooi["primary_key"])

        oois = list(run(input_ooi, get_dummy_data("raw/nikto-example.com.json")))

        software = Software(name="nginx", version="1.18.0")
        finding_type = KATFindingType(id="KAT-OUTDATED-SOFTWARE")
        software_instance = SoftwareInstance(ooi=ooi_ref, software=software.reference)
        finding = Finding(
            finding_type=finding_type.reference,
            ooi=software_instance.reference,
            description="nginx/1.18.0 appears to be outdated (current is at least 1.25.3).",
        )

        expected = [software, software_instance, finding_type, finding]

        self.assertEqual(expected, oois)

    def test_nothing_found(self):
        input_ooi = {"primary_key": "Hostname|internet|non-existing.com"}

        oois = list(run(input_ooi, get_dummy_data("raw/nikto-non-existing.com.json")))

        self.assertEqual([], oois)
