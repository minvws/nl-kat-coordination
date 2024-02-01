import json
from pathlib import Path
from unittest import TestCase

from boefjes.job_models import NormalizerMeta, NormalizerScanProfile
from boefjes.katalogus.local_repository import LocalPluginRepository
from boefjes.local import LocalNormalizerJobRunner
from tests.loading import get_dummy_data


class ScanProfileTest(TestCase):
    def test_normalizer_can_yield_scan_profile(self):
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

        self.assertIsInstance(output.scan_profiles[0], NormalizerScanProfile)
        self.assertEqual("IPAddressV4|internet|127.0.0.1", output.scan_profiles[0].reference)
        self.assertEqual(3, output.scan_profiles[0].level)

        self.assertIsInstance(output.scan_profiles[1], NormalizerScanProfile)
        self.assertEqual("IPAddressV4|internet|10.0.0.0", output.scan_profiles[1].reference)
        self.assertEqual(3, output.scan_profiles[1].level)

        self.assertIsInstance(output.scan_profiles[2], NormalizerScanProfile)
        self.assertEqual("Hostname|internet|example.com", output.scan_profiles[2].reference)
        self.assertEqual(3, output.scan_profiles[2].level)
