from ipaddress import ip_address
from unittest import TestCase
from unittest.mock import patch, Mock

from octopoes.core.service import OctopoesService
from octopoes.models import Reference, DeclaredScanProfile, InheritedScanProfile, Inheritance
from octopoes.models.path import Path
from tests.mocks.mock_ooi_types import (
    ALL_OOI_TYPES,
    MockHostname,
    MockResolvedHostname,
    MockNetwork,
    MockIPAddressV4,
    MockDNSZone,
    MockIPPort,
    MockProtocol,
    MockIPService,
)


@patch("octopoes.models.types.ALL_TYPES", ALL_OOI_TYPES)
class ScanProfileInheritanceTest(TestCase):
    def setUp(self):
        # setup a datastructure
        self.network = MockNetwork(name="internet")
        self.hostname = MockHostname(name="example.com", network=self.network.reference)
        self.ip = MockIPAddressV4(address=ip_address("1.1.1.1"), network=self.network.reference)
        self.resolved_hostname = MockResolvedHostname(hostname=self.hostname.reference, address=self.ip.reference)

    def test_calculate_inheritance_from_neighbours_empty(self):
        inheritances = OctopoesService._calculate_inheritances_from_neighbours(Mock(), {}, {})
        self.assertDictEqual({}, inheritances)

    def test_calculate_inheritance_from_neighbours_max_inheritance(self):

        # set a max level of 3 on the hostname
        self.hostname.scan_profile = DeclaredScanProfile(reference=self.hostname.reference, level=3)

        # prepare dataset for perspective from resolved hostname
        grouped_neighbours = {Path.parse("MockResolvedHostname.hostname"): [self.hostname]}
        sources = {self.hostname.reference: self.hostname.scan_profile}

        inheritances = OctopoesService._calculate_inheritances_from_neighbours(
            self.resolved_hostname, grouped_neighbours, sources
        )
        self.assertDictEqual(
            {
                str(self.hostname.reference): Inheritance(
                    parent=Reference.from_str("MockHostname|internet|example.com"),
                    source=Reference.from_str("MockHostname|internet|example.com"),
                    level=3,
                    depth=1,
                )
            },
            inheritances,
        )

    def test_calculate_inheritance_from_neighbours__same_neighbour_different_relations__highest_wins(self):

        # the inheriting ooi
        ooi = MockDNSZone(hostname=self.hostname.reference)

        # set declared scan profile on network
        self.network.scan_profile = DeclaredScanProfile(reference=self.network.reference, level=4)

        # hostname inherits 4 from network
        self.hostname.scan_profile = InheritedScanProfile(
            reference=self.hostname.reference,
            level=4,
            inheritances=[Inheritance(parent=self.network.reference, source=self.network.reference, level=4, depth=1)],
        )

        # zone is related to the same object through 2 relations
        grouped_neighbours = {
            Path.parse("MockDNSZone.<dns_zone [is MockHostname]"): [self.hostname],
            Path.parse("MockDNSZone.hostname"): [self.hostname],
        }
        sources = {self.network.reference: self.network.scan_profile}

        inheritances = OctopoesService._calculate_inheritances_from_neighbours(ooi, grouped_neighbours, sources)
        inheritance = inheritances[str(self.network.reference)]

        # higest inheritance of 2 should be applied
        self.assertEqual(self.network.reference, inheritance.source)
        self.assertEqual(self.hostname.reference, inheritance.parent)
        self.assertEqual(2, inheritance.level)
        self.assertEqual(2, inheritance.depth)

    def test_calculate_inheritance_from_neighbours__two_neighbours__declared_scan_profile_wins(self):

        # set a max level of 3 on the hostname
        self.hostname.scan_profile = DeclaredScanProfile(reference=self.hostname.reference, level=3)

        # set ip to inherit from hostname
        self.ip.scan_profile = InheritedScanProfile(
            reference=self.ip.reference,
            level=4,
            inheritances=[
                Inheritance(parent=self.hostname.reference, source=self.hostname.reference, level=3, depth=1)
            ],
        )

        # prepare dataset for perspective from resolved hostname
        grouped_neighbours = {Path.parse("MockResolvedHostname.hostname"): [self.hostname]}
        sources = {self.hostname.reference: self.hostname.scan_profile}

        inheritances = OctopoesService._calculate_inheritances_from_neighbours(
            self.resolved_hostname, grouped_neighbours, sources
        )
        inheritance = inheritances[str(self.hostname.reference)]
        self.assertEqual(self.hostname.reference, inheritance.source)
        self.assertEqual(self.hostname.reference, inheritance.parent)
        self.assertEqual(3, inheritance.level)
        self.assertEqual(1, inheritance.depth)

    def test_calculate_inheritance_from_neighbours__two_neighbours__shortest_path_wins(self):

        # set a max level of 0 on network
        self.network.scan_profile = DeclaredScanProfile(reference=self.network.reference, level=3)

        # set hostname and ip to inherit from network, hostname is less deep
        self.hostname.scan_profile = InheritedScanProfile(
            reference=self.hostname.reference,
            level=0,
            inheritances=[Inheritance(parent=self.network.reference, source=self.network.reference, level=0, depth=1)],
        )
        self.ip.scan_profile = InheritedScanProfile(
            reference=self.ip.reference,
            level=0,
            inheritances=[Inheritance(parent=self.network.reference, source=self.network.reference, level=0, depth=2)],
        )

        # prepare dataset for perspective from resolved hostname
        grouped_neighbours = {
            Path.parse("MockResolvedHostname.hostname"): [self.hostname],
            Path.parse("MockResolvedHostname.address"): [self.ip],
        }
        sources = {self.network.reference: self.network.scan_profile}

        inheritances = OctopoesService._calculate_inheritances_from_neighbours(
            self.resolved_hostname, grouped_neighbours, sources
        )
        inheritance = inheritances[str(self.network.reference)]

        # highest inheritance and shortest path of network should be applied
        self.assertEqual(self.network.reference, inheritance.source)
        self.assertEqual(self.hostname.reference, inheritance.parent)
        self.assertEqual(0, inheritance.level)
        self.assertEqual(2, inheritance.depth)

    def test_calculate_inheritance_from_neighbours__max_inheritance_level(self):

        # setup situation where ipaddress inherits from hostname and ip_port
        ip_port = MockIPPort(
            address=self.ip.reference,
            protocol=MockProtocol.TCP,
            port=80,
        )

        ip_service = MockIPService(
            ip_port=ip_port.reference,
            service="http",
        )

        # sources
        ip_service.scan_profile = DeclaredScanProfile(reference=ip_service.reference, level=1)
        self.hostname.scan_profile = DeclaredScanProfile(reference=self.hostname.reference, level=4)
        sources = {
            self.hostname.reference: self.hostname.scan_profile,
            ip_service.reference: ip_service.scan_profile,
        }

        # neighbours
        self.resolved_hostname.scan_profile = InheritedScanProfile(
            reference=self.ip.reference,
            level=4,
            inheritances=[
                Inheritance(
                    parent=self.ip.reference,
                    source=ip_service.reference,
                    level=0,
                    depth=3,
                ),
                Inheritance(
                    parent=self.hostname.reference,
                    source=self.hostname.reference,
                    level=4,
                    depth=1,
                ),
            ],
        )

        ip_port.scan_profile = InheritedScanProfile(
            reference=ip_port.reference,
            level=0,
            inheritances=[
                Inheritance(
                    parent=ip_service.reference,
                    source=ip_service.reference,
                    level=0,
                    depth=1,
                ),
            ],
        )

        # prepare dataset for perspective from resolved hostname
        grouped_neighbours = {
            Path.parse("MockIPAddressV4.<address [is MockResolvedHostname]"): [self.resolved_hostname],
            Path.parse("MockIPAddressV4.<address [is MockIPPort]"): [ip_port],
        }

        # calculate inheritances
        inheritances = OctopoesService._calculate_inheritances_from_neighbours(self.ip, grouped_neighbours, sources)

        ip_service_inheritance = inheritances[str(ip_service.reference)]
        self.assertEqual(ip_service.reference, ip_service_inheritance.source)
        self.assertEqual(2, ip_service_inheritance.depth)
        self.assertEqual(0, ip_service_inheritance.level)
        self.assertEqual(ip_port.reference, ip_service_inheritance.parent)

        hostname_inheritance = inheritances[str(self.hostname.reference)]
        self.assertEqual(self.hostname.reference, hostname_inheritance.source)
        self.assertEqual(2, hostname_inheritance.depth)
        self.assertEqual(4, hostname_inheritance.level)
        self.assertEqual(self.resolved_hostname.reference, hostname_inheritance.parent)

    def test_calculate_inheritance_from_neighbours__no_inheritance_from_child(self):

        # setup situation where ip_port inherits from ip_address
        ip_port = MockIPPort(
            address=self.ip.reference,
            protocol=MockProtocol.TCP,
            port=80,
        )

        # setup sources
        self.hostname.scan_profile = DeclaredScanProfile(reference=self.hostname.reference, level=4)
        sources = {
            self.hostname.reference: self.hostname.scan_profile,
        }

        # setup neighbours
        ip_port.scan_profile = InheritedScanProfile(
            reference=ip_port.reference,
            level=4,
            inheritances=[
                Inheritance(
                    parent=self.ip.reference,
                    source=self.hostname.reference,
                    level=4,
                    depth=3,
                )
            ],
        )

        grouped_neighbours = {
            Path.parse("MockIPAddressV4.<address [is MockIPPort]"): [ip_port],
        }

        inheritances = OctopoesService._calculate_inheritances_from_neighbours(self.ip, grouped_neighbours, sources)

        self.assertListEqual([], list(inheritances.values()))
