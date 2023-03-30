from datetime import datetime, timezone
from ipaddress import IPv4Address
from typing import Dict, List, Optional, Set

from unittest.mock import Mock

import pytest

from octopoes.repositories.ooi_repository import OOIRepository
from octopoes.repositories.scan_profile_repository import ScanProfileRepository
from octopoes.models import EmptyScanProfile, Reference, OOI, ScanProfileBase
from octopoes.models.path import Path, Direction
from octopoes.models.types import DNSZone, Hostname, IPAddressV4, Network, ResolvedHostname


@pytest.fixture
def valid_time():
    return datetime.now(timezone.utc)


class MockScanProfileRepository(ScanProfileRepository):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.profiles = {}

    def get(self, ooi_reference: Reference, valid_time: datetime) -> ScanProfileBase:
        return self.profiles[ooi_reference]

    def save(
        self, old_scan_profile: Optional[ScanProfileBase], new_scan_profile: ScanProfileBase, valid_time: datetime
    ) -> None:
        self.profiles[new_scan_profile.reference] = new_scan_profile

    def list(self, scan_profile_type: Optional[str], valid_time: datetime) -> List[ScanProfileBase]:
        if scan_profile_type:
            return [profile for profile in self.profiles.values() if profile.scan_profile_type == scan_profile_type]
        else:
            return self.profiles.values()

    def delete(self, scan_profile: ScanProfileBase, valid_time: datetime) -> None:
        del self.profiles[scan_profile.reference]


@pytest.fixture
def scan_profile_repository():
    return MockScanProfileRepository(Mock())


class MockOOIRepository(OOIRepository):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.oois = {}

    def save(self, ooi: OOI, valid_time: datetime, end_valid_time: Optional[datetime] = None) -> None:
        self.oois[ooi.reference] = ooi

    def get_bulk(self, references: Set[Reference], valid_time: datetime) -> Dict[str, OOI]:
        return {ooi.primary_key: ooi for ooi in self.oois.values() if ooi.reference in references}

    def list_neighbours(self, references: Set[Reference], paths: Set[Path], valid_time: datetime) -> Set[OOI]:
        neighbours = set()

        for path in paths:
            # Neighbours should have paths of length 1
            assert len(path.segments) == 1
            segment = path.segments[0]
            if segment.direction == Direction.OUTGOING:
                for ref in references:
                    neighbour_ref = getattr(self.oois[ref], segment.property_name)
                    neighbours.add(self.oois[neighbour_ref])
            else:
                for ooi in self.oois.values():
                    if not isinstance(ooi, segment.target_type):
                        continue

                    for ref in references:
                        if getattr(ooi, segment.property_name) == ref:
                            neighbours.add(ooi)

        return neighbours

    def list_oois_without_scan_profile(self, valid_time: datetime) -> Set[Reference]:
        return set()


@pytest.fixture
def ooi_repository():
    return MockOOIRepository(Mock())


def add_ooi(ooi, ooi_repository, scan_profile_repository, valid_time):
    ooi_repository.save(ooi, valid_time)
    scan_profile_repository.save(None, EmptyScanProfile(reference=ooi.reference), valid_time)
    return ooi


@pytest.fixture
def network(ooi_repository, scan_profile_repository, valid_time):
    return add_ooi(Network(name="internet"), ooi_repository, scan_profile_repository, valid_time)


@pytest.fixture
def dns_zone(network, ooi_repository, hostname, scan_profile_repository, valid_time):
    ooi = add_ooi(
        DNSZone(name="example.com.", hostname=hostname.reference, network=network.reference),
        ooi_repository,
        scan_profile_repository,
        valid_time,
    )
    hostname.dns_zone = ooi.reference
    return ooi


@pytest.fixture
def hostname(network, ooi_repository, scan_profile_repository, valid_time):
    return add_ooi(
        Hostname(name="example.com.", network=network.reference),
        ooi_repository,
        scan_profile_repository,
        valid_time,
    )


@pytest.fixture
def ipaddressv4(network, ooi_repository, scan_profile_repository, valid_time):
    return add_ooi(
        IPAddressV4(network=network.reference, address=IPv4Address("1.1.1.1")),
        ooi_repository,
        scan_profile_repository,
        valid_time,
    )


@pytest.fixture
def resolved_hostname(hostname, ipaddressv4, ooi_repository, scan_profile_repository, valid_time):
    return add_ooi(
        ResolvedHostname(hostname=hostname.reference, address=ipaddressv4.reference),
        ooi_repository,
        scan_profile_repository,
        valid_time,
    )
