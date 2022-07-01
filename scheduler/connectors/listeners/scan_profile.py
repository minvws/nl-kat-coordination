from typing import List, Optional

from scheduler.connectors.errors import exception_handler
from scheduler.models import OOI
from scheduler.models import ScanProfile as ScanProfileModel

from .listeners import RabbitMQ


class ScanProfile(RabbitMQ):
    name = "scan_profile"

    @exception_handler
    def get_latest_object(self, queue: str) -> Optional[OOI]:
        response = self.get(queue)
        if response is None:
            return None

        scan_profile = ScanProfileModel(**response)
        ooi = OOI(
            primary_key=scan_profile.reference,
            ooi_type=scan_profile.ooi_type,
            scan_profile=scan_profile,
        )

        return ooi

    @exception_handler
    def get_latest_objects(self, queue: str, n: int) -> Optional[List[OOI]]:
        oois: List[OOI] = []

        for _ in range(n):
            ooi = self.get_latest_object(queue=queue)
            if ooi is None:
                break

            oois.append(ooi)

        return oois
