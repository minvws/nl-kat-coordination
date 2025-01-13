import os
from datetime import datetime
from unittest.mock import Mock

import pytest
from nibbles.missing_spf.nibble import NIBBLE as missing_spf_nibble
from nibbles.runner import NibblesRunner

from octopoes.core.service import OctopoesService
from octopoes.models.ooi.dns.records import NXDOMAIN, DNSTXTRecord
from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.ooi.email_security import DNSSPFRecord
from octopoes.models.ooi.network import Network

if os.environ.get("CI") != "1":
    pytest.skip("Needs XTDB multinode container.", allow_module_level=True)


def test_missing_spf_nibble_with_and_without_nx(
    xtdb_octopoes_service: OctopoesService, event_manager: Mock, valid_time: datetime
):
    nibbler = NibblesRunner(
        xtdb_octopoes_service.ooi_repository,
        xtdb_octopoes_service.origin_repository,
        xtdb_octopoes_service.nibbler.nibble_repository,
    )
    xtdb_octopoes_service.nibbler.disable()
    nibbler.nibbles = {missing_spf_nibble.id: missing_spf_nibble}
    network = Network(name="internet")
    xtdb_octopoes_service.ooi_repository.save(network, valid_time)
    hostname = Hostname(name="test", network=network.reference)
    xtdb_octopoes_service.ooi_repository.save(hostname, valid_time)

    event_manager.complete_process_events(xtdb_octopoes_service)
    xtdb_hostname = xtdb_octopoes_service.ooi_repository.get(hostname.reference, valid_time)

    result = nibbler.infer([xtdb_hostname], valid_time)
    event_manager.complete_process_events(xtdb_octopoes_service)

    assert (xtdb_hostname, None, None) in result[hostname][missing_spf_nibble.id]
    assert len(result[hostname][missing_spf_nibble.id][(xtdb_hostname, None, None)]) == 2

    nx_domain = NXDOMAIN(hostname=hostname.reference)
    xtdb_octopoes_service.ooi_repository.save(nx_domain, valid_time)
    event_manager.complete_process_events(xtdb_octopoes_service)
    xtdb_nx = xtdb_octopoes_service.ooi_repository.get(nx_domain.reference, valid_time)
    result = nibbler.infer([xtdb_nx], valid_time)
    event_manager.complete_process_events(xtdb_octopoes_service)

    assert (xtdb_hostname, None, xtdb_nx) in result[nx_domain][missing_spf_nibble.id]
    assert len(result[nx_domain][missing_spf_nibble.id][(xtdb_hostname, None, xtdb_nx)]) == 0


def test_missing_spf_nibble_with_and_without_spf(
    xtdb_octopoes_service: OctopoesService, event_manager: Mock, valid_time: datetime
):
    nibbler = NibblesRunner(
        xtdb_octopoes_service.ooi_repository,
        xtdb_octopoes_service.origin_repository,
        xtdb_octopoes_service.nibbler.nibble_repository,
    )
    xtdb_octopoes_service.nibbler.disable()
    nibbler.nibbles = {missing_spf_nibble.id: missing_spf_nibble}
    network = Network(name="internet")
    xtdb_octopoes_service.ooi_repository.save(network, valid_time)
    hostname = Hostname(name="test", network=network.reference)
    xtdb_octopoes_service.ooi_repository.save(hostname, valid_time)

    event_manager.complete_process_events(xtdb_octopoes_service)
    xtdb_hostname = xtdb_octopoes_service.ooi_repository.get(hostname.reference, valid_time)

    result = nibbler.infer([xtdb_hostname], valid_time)
    event_manager.complete_process_events(xtdb_octopoes_service)

    assert (xtdb_hostname, None, None) in result[hostname][missing_spf_nibble.id]
    assert len(result[hostname][missing_spf_nibble.id][(xtdb_hostname, None, None)]) == 2

    txt_record = DNSTXTRecord(hostname=hostname.reference, value="test")
    xtdb_octopoes_service.ooi_repository.save(txt_record, valid_time)
    spf_record = DNSSPFRecord(dns_txt_record=txt_record.reference, value="test")
    xtdb_octopoes_service.ooi_repository.save(spf_record, valid_time)
    event_manager.complete_process_events(xtdb_octopoes_service)
    xtdb_spf_record = xtdb_octopoes_service.ooi_repository.get(spf_record.reference, valid_time)
    result = nibbler.infer([xtdb_spf_record], valid_time)
    event_manager.complete_process_events(xtdb_octopoes_service)

    assert (xtdb_hostname, xtdb_spf_record, None) in result[spf_record][missing_spf_nibble.id]
    assert len(result[spf_record][missing_spf_nibble.id][(xtdb_hostname, xtdb_spf_record, None)]) == 0


def test_missing_spf_nibble_non_tld(xtdb_octopoes_service: OctopoesService, event_manager: Mock, valid_time: datetime):
    nibbler = NibblesRunner(
        xtdb_octopoes_service.ooi_repository,
        xtdb_octopoes_service.origin_repository,
        xtdb_octopoes_service.nibbler.nibble_repository,
    )
    xtdb_octopoes_service.nibbler.disable()
    nibbler.nibbles = {missing_spf_nibble.id: missing_spf_nibble}
    network = Network(name="internet")
    xtdb_octopoes_service.ooi_repository.save(network, valid_time)
    hostname = Hostname(name="example.example.com", network=network.reference)
    xtdb_octopoes_service.ooi_repository.save(hostname, valid_time)

    event_manager.complete_process_events(xtdb_octopoes_service)
    xtdb_hostname = xtdb_octopoes_service.ooi_repository.get(hostname.reference, valid_time)

    result = nibbler.infer([xtdb_hostname], valid_time)
    event_manager.complete_process_events(xtdb_octopoes_service)

    assert (xtdb_hostname, None, None) in result[hostname][missing_spf_nibble.id]
    assert len(result[hostname][missing_spf_nibble.id][(xtdb_hostname, None, None)]) == 0
