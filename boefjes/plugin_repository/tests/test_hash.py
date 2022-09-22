import shutil
import tempfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

import diskcache

from boefjes.plugin_repository.tests.common import FIXTURES_DIR
from boefjes.plugin_repository.utils.cache import get_or_create_cache
from boefjes.plugin_repository.utils.hash import Hasher

FILE_1 = FIXTURES_DIR / "dump-1"
FILE_2 = FIXTURES_DIR / "dump-2"

TEMP_CACHE_DIR = Path(tempfile.mkdtemp())
CACHE = get_or_create_cache(TEMP_CACHE_DIR)


class TestHash(TestCase):
    def setUp(self) -> None:
        cache = diskcache.Cache(TEMP_CACHE_DIR.as_posix())
        self.hasher = Hasher(cache)

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(TEMP_CACHE_DIR)

    def test_generate_hash(self):
        self.assertEqual(
            "b6ca0868bca6a2926b70aa1a71592038d9030fe26d4214edcfbd6cf41f2f4654",
            self.hasher.generate_hash(FILE_1),
        )

    def test_get_or_generate_hash(self):
        generate_hash = self.hasher.generate_hash

        with patch.object(self.hasher, "generate_hash") as mock_generate_hash:
            mock_generate_hash.side_effect = generate_hash

            self.assertEqual(
                "b6ca0868bca6a2926b70aa1a71592038d9030fe26d4214edcfbd6cf41f2f4654",
                self.hasher.get_or_generate_hash(FILE_1),
            )
            # call again to confirm
            self.assertEqual(
                "b6ca0868bca6a2926b70aa1a71592038d9030fe26d4214edcfbd6cf41f2f4654",
                self.hasher.get_or_generate_hash(FILE_1),
            )
            mock_generate_hash.assert_called_once_with(FILE_1)

    def test_generate_combined_hash(self):
        self.assertEqual(
            "064d85189dc5b718bf0f1e8005fce8d86a4c364c548566c1db5faddb26600b85",
            self.hasher.generate_combined_hash(FILE_1, FILE_2),
        )

    def test_get_or_generate_combined_hash(self):
        generate_combined_hash = self.hasher.generate_combined_hash

        with patch.object(
            self.hasher, "generate_combined_hash"
        ) as mock_generate_combined_hash:
            mock_generate_combined_hash.side_effect = generate_combined_hash

            self.assertEqual(
                "064d85189dc5b718bf0f1e8005fce8d86a4c364c548566c1db5faddb26600b85",
                self.hasher.get_or_generate_combined_hash(FILE_1, FILE_2),
            )
            # call again to confirm
            self.assertEqual(
                "064d85189dc5b718bf0f1e8005fce8d86a4c364c548566c1db5faddb26600b85",
                self.hasher.get_or_generate_combined_hash(FILE_1, FILE_2),
            )
            mock_generate_combined_hash.assert_called_once_with(FILE_1, FILE_2)
