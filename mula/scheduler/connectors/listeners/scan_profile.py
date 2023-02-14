from typing import List, Optional

from scheduler.connectors.errors import exception_handler
from scheduler.models import ScanProfileMutation as ScanProfileMutationModel

from .listeners import RabbitMQ


class ScanProfileMutation(RabbitMQ):
    name = "scan_profile_mutation"

    @exception_handler
    def get_scan_profile_mutation(self, queue: str) -> Optional[ScanProfileMutationModel]:
        response = self.get(queue)
        if response is None:
            return None

        return ScanProfileMutationModel(**response)

    @exception_handler
    def get_scan_profile_mutations(self, queue: str, n: int) -> Optional[List[ScanProfileMutationModel]]:
        oois: List[ScanProfileMutationModel] = []

        for _ in range(n):
            ooi = self.get_scan_profile_mutation(queue=queue)
            if ooi is None:
                break

            oois.append(ooi)

        return oois
