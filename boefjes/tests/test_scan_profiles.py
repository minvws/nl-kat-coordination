import json
import os
from pathlib import Path
from unittest import TestCase, mock

import pytest
from pydantic import ValidationError

from boefjes.config import Settings
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

        raw = json.dumps(
            {
                "ip_addresses": [{"ip_address": "127.0.0.1"}, {"ip_address": "10.0.0.0"}],
                "domains": [{"domain": "example.com"}],
            }
        )
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

    def test_job_handler_respects_whitelist(self):
        raw = {
            "ip_addresses": [{"ip_address": "127.0.0.1"}, {"ip_address": "10.0.0.0"}],
            "domains": [{"domain": "example.com"}],
        }
        bytes_mock = mock.Mock()
        bytes_mock.get_raw.return_value = json.dumps(raw)
        octopoes = mock.Mock()

        local_repository = LocalPluginRepository(Path(__file__).parent.parent / "boefjes" / "plugins")
        runner = LocalNormalizerJobRunner(local_repository)
        meta = NormalizerMeta.model_validate_json(get_dummy_data("external_db.json"))

        os.environ["BOEFJES_SCAN_PROFILE_WHITELIST"] = '{"x": 5}'
        with pytest.raises(ValidationError):
            Settings()

        os.environ["BOEFJES_SCAN_PROFILE_WHITELIST"] = '{"x": -1}'
        with pytest.raises(ValidationError):
            Settings()

        os.environ["BOEFJES_SCAN_PROFILE_WHITELIST"] = '{"x": 3}'
        NormalizerHandler(runner, bytes_mock, lambda x: octopoes, Settings().scan_profile_whitelist).handle(meta)
        assert octopoes.save_many_scan_profiles.call_count == 0

        os.environ["BOEFJES_SCAN_PROFILE_WHITELIST"] = '{"kat_external_db_normalize": 2}'
        NormalizerHandler(runner, bytes_mock, lambda x: octopoes, Settings().scan_profile_whitelist).handle(meta)
        assert octopoes.save_many_scan_profiles.call_count == 0

        os.environ["BOEFJES_SCAN_PROFILE_WHITELIST"] = '{"kat_external_db_normalize": 3}'
        NormalizerHandler(runner, bytes_mock, lambda x: octopoes, Settings().scan_profile_whitelist).handle(meta)
        assert octopoes.save_many_scan_profiles.call_count == 1

        os.environ["BOEFJES_SCAN_PROFILE_WHITELIST"] = '{"kat_external_db_normalize": 4, "abc": 0}'
        NormalizerHandler(runner, bytes_mock, lambda x: octopoes, Settings().scan_profile_whitelist).handle(meta)
        assert octopoes.save_many_scan_profiles.call_count == 2
