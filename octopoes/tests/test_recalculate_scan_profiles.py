from unittest.mock import Mock

from octopoes.core.service import OctopoesService
from octopoes.models import DeclaredScanProfile


def test_recalculate_no_profiles(valid_time, scan_profile_repository, ooi_repository):
    octopoes = OctopoesService(ooi_repository, Mock(), Mock(), scan_profile_repository)

    octopoes.recalculate_scan_profiles(valid_time)


def test_recalculate_only_empty_profiles(valid_time, resolved_hostname, scan_profile_repository, ooi_repository):
    octopoes = OctopoesService(ooi_repository, Mock(), Mock(), scan_profile_repository)

    octopoes.recalculate_scan_profiles(valid_time)


def test_recalculate_inherent(
    valid_time, dns_zone, hostname, resolved_hostname, ipaddressv4, scan_profile_repository, ooi_repository
):
    octopoes = OctopoesService(ooi_repository, Mock(), Mock(), scan_profile_repository)

    scan_profile_repository.save(None, DeclaredScanProfile(reference=hostname.reference, level=4), valid_time)

    octopoes.recalculate_scan_profiles(valid_time)

    assert scan_profile_repository.get(ipaddressv4.reference, valid_time).level == 4
    assert scan_profile_repository.get(resolved_hostname.reference, valid_time).level == 4
    assert scan_profile_repository.get(dns_zone.reference, valid_time).level == 1


def test_recalculate_inherent_max(
    valid_time, dns_zone, resolved_hostname, ipaddressv4, scan_profile_repository, ooi_repository
):
    octopoes = OctopoesService(ooi_repository, Mock(), Mock(), scan_profile_repository)

    scan_profile_repository.save(None, DeclaredScanProfile(reference=dns_zone.reference, level=4), valid_time)

    octopoes.recalculate_scan_profiles(valid_time)

    assert scan_profile_repository.get(resolved_hostname.reference, valid_time).level == 2
    assert scan_profile_repository.get(ipaddressv4.reference, valid_time).level == 2
    assert scan_profile_repository.get(resolved_hostname.reference, valid_time).level == 2


def test_recalculate_inherent_recalculate(
    valid_time, dns_zone, hostname, resolved_hostname, ipaddressv4, scan_profile_repository, ooi_repository
):
    octopoes = OctopoesService(ooi_repository, Mock(), Mock(), scan_profile_repository)

    scan_profile_repository.save(None, DeclaredScanProfile(reference=hostname.reference, level=3), valid_time)

    octopoes.recalculate_scan_profiles(valid_time)

    assert scan_profile_repository.get(ipaddressv4.reference, valid_time).level == 3
    assert scan_profile_repository.get(resolved_hostname.reference, valid_time).level == 3
    assert scan_profile_repository.get(dns_zone.reference, valid_time).level == 1

    octopoes.recalculate_scan_profiles(valid_time)

    assert scan_profile_repository.get(ipaddressv4.reference, valid_time).level == 3
    assert scan_profile_repository.get(resolved_hostname.reference, valid_time).level == 3
    assert scan_profile_repository.get(dns_zone.reference, valid_time).level == 1

    profile = DeclaredScanProfile(reference=hostname.reference, level=2)
    scan_profile_repository.save(None, profile, valid_time)

    octopoes.recalculate_scan_profiles(valid_time)

    assert scan_profile_repository.get(ipaddressv4.reference, valid_time).level == 2
    assert scan_profile_repository.get(resolved_hostname.reference, valid_time).level == 2
    assert scan_profile_repository.get(dns_zone.reference, valid_time).level == 1

    scan_profile_repository.delete(profile, valid_time)

    octopoes.recalculate_scan_profiles(valid_time)

    assert scan_profile_repository.get(ipaddressv4.reference, valid_time).level == 0
    assert scan_profile_repository.get(resolved_hostname.reference, valid_time).level == 0
    assert scan_profile_repository.get(dns_zone.reference, valid_time).level == 0
