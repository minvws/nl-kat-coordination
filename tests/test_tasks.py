from typing import List
from unittest import TestCase

from job import BoefjeMeta
from katalogus.models import Boefje, Normalizer, Bit, PluginType
from tasks import normalizers_for_meta


class TaskTest(TestCase):
    def setUp(self) -> None:
        self.boefjes = [
            Boefje(
                id="test-boefje-1",
                repository_id="",
                consumes={"SomeOOI"},
                produces=["test-boef-1", "test/text"],
            ),
            Boefje(
                id="test-boefje-2",
                repository_id="",
                consumes={"SomeOOI"},
                produces=["test-boef-2", "test/text"],
            ),
            Boefje(
                id="test-boefje-3",
                repository_id="",
                consumes={"SomeOOI"},
                produces=["test-boef-3", "test/plain"],
            ),
            Boefje(
                id="test-boefje-4",
                repository_id="",
                consumes={"SomeOOI"},
                produces=["test-boef-4", "test/and-simple"],
            ),
        ]
        self.normalizers = [
            Normalizer(
                id="test-normalizer-1",
                repository_id="",
                consumes=["test-boef-3", "test/text"],
                produces=["SomeOOI", "OtherOOI"],
            ),
            Normalizer(
                id="test-normalizer-2",
                repository_id="",
                consumes=["test/text"],
                produces=["SomeOtherOOI"],
            ),
        ]
        self.bits = [
            Bit(
                id="test-bit-1",
                repository_id="",
                consumes="SomeOOI",
                produces=["SomeOOI"],
                parameters=[],
            ),
            Bit(
                id="test-bit-2",
                repository_id="",
                consumes="SomeOOI",
                produces=["SomeOOI", "SomeOtherOOI"],
                parameters=[],
            ),
        ]
        self.plugins: List[PluginType] = self.boefjes + self.normalizers + self.bits

    def test_all_normalizers_match_some_boefje_mime_type(self):
        self.assertListEqual(
            normalizers_for_meta(self._get_boefje_meta(), self.plugins),
            self.normalizers,
        )

    def test_one_normalizers_matches_some_boefje_mime_type(self):
        boefje_meta = self._get_boefje_meta()
        boefje_meta.boefje.id = "test-boefje-3"
        self.assertListEqual(
            normalizers_for_meta(boefje_meta, self.plugins), [self.normalizers[0]]
        )

    def _get_boefje_meta(self):
        return BoefjeMeta(
            id="c188ef6b-b756-4cb0-9cb2-0db776e3cce3",
            boefje={"id": "test-boefje-1", "version": "9"},
            input_ooi="Hostname|internet|example.com",
            arguments={},
            organization="_dev",
        )
