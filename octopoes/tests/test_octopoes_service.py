from datetime import datetime, timezone
from ipaddress import ip_address
from unittest import TestCase
from unittest.mock import Mock, patch

from bits.definitions import BitDefinition
from octopoes.core.service import OctopoesService
from octopoes.events.events import OOIDBEvent, OperationType, OriginDBEvent
from octopoes.models import Reference
from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.ooi.network import IPAddress, Network, IPAddressV4
from octopoes.models.origin import Origin, OriginType


def mocked_bit_definitions():
    return {
        "fake-hostname-bit": BitDefinition(
            id="fake-hostname-bit", consumes=Hostname, module="fake_module", parameters=[]
        ),
        "fake-ipaddress-bit": BitDefinition(id="fake-bit", consumes=IPAddress, module="fake_module", parameters=[]),
    }


class OctopoesServiceTest(TestCase):
    def setUp(self) -> None:
        self.octopoes = OctopoesService(Mock(), Mock(), Mock(), Mock())
        self.valid_time = datetime.now(timezone.utc)

    def tearDown(self) -> None:
        pass

    @patch("octopoes.core.service.get_bit_definitions", mocked_bit_definitions)
    def test_process_ooi_create_event(self):

        # upon creation of a new ooi
        ooi = Hostname(network=Network(name="internet").reference, name="example.com")
        self.octopoes.process_event(
            OOIDBEvent(
                operation_type=OperationType.CREATE,
                valid_time=self.valid_time,
                client="_dev",
                old_data=None,
                new_data=ooi,
            )
        )

        # octopoes should create a new origin, because there is a matching bit definition
        self.octopoes.origin_repository.save.assert_called_once_with(
            Origin(
                origin_type=OriginType.INFERENCE,
                method="fake-hostname-bit",
                source=ooi.reference,
            ),
            self.valid_time,
        )

    @patch("octopoes.core.service.get_bit_definitions", mocked_bit_definitions)
    def test_process_event_abstract_bit_consumes(self):

        # upon creation of a new ooi
        ooi = IPAddressV4(network=Network(name="internet").reference, address=ip_address("1.1.1.1"))
        self.octopoes.process_event(
            OOIDBEvent(
                operation_type=OperationType.CREATE,
                valid_time=self.valid_time,
                client="_dev",
                old_data=None,
                new_data=ooi,
            )
        )

        # octopoes should create a new origin, because there is a matching bit definition (w/ abstract class)
        self.octopoes.origin_repository.save.assert_called_once_with(
            Origin(
                origin_type=OriginType.INFERENCE,
                method="fake-ipaddress-bit",
                source=ooi.reference,
            ),
            self.valid_time,
        )

    def test_on_update_origin(self):

        # when the result of an origin changes
        old_data = Origin(
            origin_type=OriginType.OBSERVATION,
            method="test-boefje",
            source=Reference.from_str("Hostname|internet|example.com"),
            result=[Reference.from_str("IPAddress|internet|1.1.1.1")],
        )
        new_data = Origin(
            origin_type=OriginType.OBSERVATION,
            method="test-boefje",
            source=Reference.from_str("Hostname|internet|example.com"),
        )
        event = OriginDBEvent(
            operation_type=OperationType.UPDATE,
            valid_time=self.valid_time,
            client="_dev",
            old_data=old_data,
            new_data=new_data,
        )

        # and the deferenced ooi is no longer referred to by any origins
        self.octopoes.origin_repository.list_by_result.return_value = []
        self.octopoes.process_event(event)

        # the ooi should be deleted
        self.octopoes.ooi_repository.delete.assert_called_once_with(
            Reference.from_str("IPAddress|internet|1.1.1.1"), self.valid_time
        )
