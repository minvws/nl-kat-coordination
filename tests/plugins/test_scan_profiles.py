import json
import uuid
from datetime import datetime

from files.models import File, NamedContent
from katalogus.boefjes.kat_external_db.normalize import run
from katalogus.boefjes.normalizer_handler import LocalNormalizerHandler
from katalogus.worker.job_models import NormalizerMeta
from octopoes.models import DeclaredScanProfile, Reference
from octopoes.models.ooi.dns.zone import Hostname
from tasks.models import Task
from tests.conftest import get_dummy_data

RAW_DATA = json.dumps(
    {"ip_addresses": [{"address": "127.0.0.1"}, {"address": "10.0.0.0"}], "domains": [{"name": "example.com"}]}
)


def test_normalizer_can_yield_scan_profiles():
    meta = NormalizerMeta.model_validate_json(get_dummy_data("external_db.json"))
    output = LocalNormalizerHandler._parse_results(
        meta, run(meta.raw_data.boefje_meta.input_ooi_data, bytes(RAW_DATA, "UTF-8"))
    )

    assert len(output.observations) == 1
    assert len(output.observations[0].results) == 3
    assert len(output.scan_profiles) == 3

    profile = output.scan_profiles[0]
    assert isinstance(profile, DeclaredScanProfile)
    assert profile.reference == "IPAddressV4|internet|127.0.0.1"
    assert profile.level == 3

    profile = output.scan_profiles[1]
    assert isinstance(profile, DeclaredScanProfile)
    assert profile.reference == "IPAddressV4|internet|10.0.0.0"
    assert profile.level == 3

    profile = output.scan_profiles[2]
    assert isinstance(profile, DeclaredScanProfile)
    assert profile.reference == "Hostname|internet|example.com"
    assert profile.level == 3


def test_job_handler_respects_whitelist(local_repository, organization, mocker):
    octopoes_mock = mocker.Mock()
    octopoes_mock.get.return_value = Hostname(name="test", network=Reference.from_str("Network|test"))

    meta = NormalizerMeta.model_validate_json(get_dummy_data("external_db.json"))
    raw = File.objects.create(file=NamedContent(RAW_DATA))
    meta.raw_data.id = raw.id

    task = Task(
        id=uuid.uuid4(),
        organization=organization,
        type="boefje",
        created_at=datetime.now(),
        modified_at=datetime.now(),
        data=meta.model_dump(mode="json"),
    )

    LocalNormalizerHandler(local_repository, octopoes_mock, {"x": 3}).handle(task)
    assert octopoes_mock.save_many_scan_profiles.call_count == 0

    LocalNormalizerHandler(local_repository, octopoes_mock, {"kat_external_db_normalize": 2}).handle(task)
    assert octopoes_mock.save_many_scan_profiles.call_count == 1
    assert octopoes_mock.save_many_scan_profiles.call_args[0][0][0].level == 2

    LocalNormalizerHandler(local_repository, octopoes_mock, {"kat_external_db_normalize": 3}).handle(task)
    assert octopoes_mock.save_many_scan_profiles.call_count == 2
    assert octopoes_mock.save_many_scan_profiles.call_args[0][0][0].level == 3

    LocalNormalizerHandler(local_repository, octopoes_mock, {"kat_external_db_normalize": 4, "abc": 0}).handle(task)
    assert octopoes_mock.save_many_scan_profiles.call_count == 3
