import json
from pathlib import Path
from unittest import TestCase

from boefjes.job_handler import NormalizerHandler
from boefjes.job_models import NormalizerMeta, NormalizerScanProfile
from boefjes.katalogus.local_repository import LocalPluginRepository
from boefjes.local import LocalNormalizerJobRunner
from tests.loading import get_dummy_data


class ScanProfileTest(TestCase):
    def test_normalizer_can_yield_scan_profiles(self):
        local_repository = LocalPluginRepository(Path(__file__).parent.parent / "boefjes" / "plugins")
        runner = LocalNormalizerJobRunner(local_repository)
        meta = NormalizerMeta.model_validate_json(get_dummy_data("external_db.json"))

        raw = json.dumps({
            "ip_addresses": [{"ip_address": "127.0.0.1"}, {"ip_address": "10.0.0.0"}],
            "domains": [{"domain": "example.com"}],
        })
        output = runner.run(meta, bytes(raw, "UTF-8"))

        self.assertEqual(1, len(output.observations))
        self.assertEqual(3, len(output.observations[0].results))
        self.assertEqual(3, len(output.scan_profiles))

        profile = output.scan_profiles[0]
        self.assertIsInstance(profile, NormalizerScanProfile)
        self.assertEqual("IPAddressV4|internet|127.0.0.1", profile.reference)
        self.assertEqual(3, profile.level)

        profile = output.scan_profiles[1]
        self.assertIsInstance(profile, NormalizerScanProfile)
        self.assertEqual("IPAddressV4|internet|10.0.0.0", profile.reference)
        self.assertEqual(3, profile.level)

        profile = output.scan_profiles[2]
        self.assertIsInstance(profile, NormalizerScanProfile)
        self.assertEqual("Hostname|internet|example.com", profile.reference)
        self.assertEqual(3, profile.level)

    def test_whitelist_approves_right_format(self):
        self.assertTrue(NormalizerHandler._matches_whitelist(
            NormalizerScanProfile(scan_profile_type="declared", level=2), "test", "test=2"
        ))
        self.assertTrue(NormalizerHandler._matches_whitelist(
            NormalizerScanProfile(scan_profile_type="declared", level=2), "test", "test=2,abc=8"  # Early return!
        ))
        self.assertTrue(NormalizerHandler._matches_whitelist(
            NormalizerScanProfile(scan_profile_type="declared", level=3), "test", "abc=2,test=4,"
        ))
        self.assertFalse(NormalizerHandler._matches_whitelist(
            NormalizerScanProfile(scan_profile_type="declared", level=2), "test", "test=1,abc=1,def=0"
        ))
        self.assertFalse(NormalizerHandler._matches_whitelist(
            NormalizerScanProfile(scan_profile_type="declared", level=0), "test", "abc=1,def=0"
        ))
        self.assertFalse(NormalizerHandler._matches_whitelist(
            NormalizerScanProfile(scan_profile_type="declared", level=4), "ah", "test=4,abc=1,def=0"
        ))
