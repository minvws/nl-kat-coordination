from typing import List
from unittest import TestCase, mock

from octopoes.models import Reference
from octopoes.models.ooi.network import Network

from job import BoefjeMeta
from job_handler import handle_boefje_job
from katalogus.models import Boefje, Normalizer, Bit, PluginType
from runner import LocalBoefjeJobRunner
from tasks import normalizers_for_meta, handle_boefje

import boefjes.models


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
        ).copy()

    @mock.patch("job_handler.bytes_api_client")
    def test_handle_boefje_with_exception(
        self,
        mock_bytes_api_client,
    ):
        meta = BoefjeMeta(
            id="some-random-job-id",
            boefje={"id": "dummy-with-exception"},
            input_ooi="Network|internet",
            arguments={},
            organization="_dev",
        )
        boefje = boefjes.models.Boefje(
            id="dummy-with-exception",
            repository_id="",
            name="dummy",
            module="modules.dummy_boefje_runtime_exception",
            description="",
            input_ooi={Network},
            produces=set(),
            consumes=set(),
            dispatches={},
        )

        handle_boefje_job(meta, LocalBoefjeJobRunner(meta, boefje, "tests"))

        mock_bytes_api_client.save_boefje_meta.assert_called_once_with(meta)
        mock_bytes_api_client.save_raw.assert_called_once_with(
            "some-random-job-id", "dummy error", {"error/boefje"}
        )
