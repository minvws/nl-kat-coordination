from unittest import TestCase
from unittest.mock import patch

from octopoes.models import Reference, DeclaredScanProfile, InheritedScanProfile
from octopoes.repositories.scan_profile_repository import XTDBScanProfileRepository
from tests.mocks.mock_ooi_types import (
    ALL_OOI_TYPES,
    MockNetwork,
    MockIPAddressV4,
)


@patch("octopoes.models.types.ALL_TYPES", ALL_OOI_TYPES)
class ScanProfileRepositoryTest(TestCase):
    def setUp(self) -> None:
        ...

    def test_serialize_declared(self):
        scan_profile = DeclaredScanProfile(
            reference=Reference.from_str("MockIPAddressV4|internet|1.1.1.1"),
            level=1,
        )

        serialized = XTDBScanProfileRepository.serialize(scan_profile)

        self.assertEqual("ScanProfile|MockIPAddressV4|internet|1.1.1.1", serialized["crux.db/id"])
        self.assertEqual("ScanProfile", serialized["type"])
        self.assertEqual("declared", serialized["scan_profile_type"])
        self.assertEqual(1, serialized["level"])

    def test_serialize_inherited(self):
        network = MockNetwork(name="internet")
        ip = MockIPAddressV4(address="1.1.1.1", network=network.reference)

        scan_profile = InheritedScanProfile(
            reference=ip.reference,
            level=2,
        )
        serialized = XTDBScanProfileRepository.serialize(scan_profile)

        self.assertEqual("ScanProfile|MockIPAddressV4|internet|1.1.1.1", serialized["crux.db/id"])
        self.assertEqual("ScanProfile", serialized["type"])
        self.assertEqual("inherited", serialized["scan_profile_type"])
        self.assertEqual(2, serialized["level"])

    def test_deserialize_declared(
        self,
    ):
        serialized = {
            "reference": "MockIPAddressV4|internet|1.1.1.1",
            "level": 1,
            "scan_profile_type": "declared",
            "crux.db/id": "ScanProfile|MockIPAddressV4|internet|1.1.1.1",
            "type": "ScanProfile",
        }
        scan_profile = XTDBScanProfileRepository.deserialize(serialized)
        self.assertIsInstance(scan_profile, DeclaredScanProfile)
        self.assertEqual(Reference.from_str("MockIPAddressV4|internet|1.1.1.1"), scan_profile.reference)
        self.assertEqual("declared", scan_profile.scan_profile_type)
        self.assertEqual(1, scan_profile.level)

    def test_deserialize_inherited_legacy(
        self,
    ):
        serialized = {
            "reference": "MockIPAddressV4|internet|1.1.1.2",
            "level": 2,
            "scan_profile_type": "inherited",
            "crux.db/id": "ScanProfile|MockIPAddressV4|internet|1.1.1.1",
            "type": "ScanProfile",
            "inheritances": [
                {
                    "parent": "MockNetwork|internet2",
                    "source": "MockNetwork|internet2",
                    "level": 2,
                    "depth": 1,
                }
            ],
        }
        scan_profile = XTDBScanProfileRepository.deserialize(serialized)
        self.assertIsInstance(scan_profile, InheritedScanProfile)
        self.assertEqual(Reference.from_str("MockIPAddressV4|internet|1.1.1.2"), scan_profile.reference)
        self.assertEqual("inherited", scan_profile.scan_profile_type)
        self.assertEqual(2, scan_profile.level)
