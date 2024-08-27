from datetime import datetime
from itertools import chain, product

from nibbles.definitions import NibbleDefinition, get_nibble_definitions
from octopoes.models import OOI
from octopoes.models.types import type_by_name
from octopoes.repositories.ooi_repository import OOIRepository


def otype(ooi: OOI) -> type[OOI]:
    return type_by_name(ooi.get_ooi_type())


class NibblesRunner:
    def __init__(self, ooi_repository: OOIRepository):
        self.ooi_repository = ooi_repository
        self.nibbles: list[NibbleDefinition] = get_nibble_definitions()

    def run(self, ooi: OOI, objects_by_type: dict[type[OOI], set[OOI]]) -> set[OOI]:
        retval = set()
        for nibble in list(filter(lambda x: type(ooi) in x.signature, self.nibbles)):
            radix = [objects_by_type[sgn] for sgn in nibble.signature]
            retval |= nibble(*list(filter(lambda x: ooi in x, product(radix))))
        return retval

    def infer(self, stack: list[OOI]) -> set[OOI]:
        signatures_object_types: set[type[OOI]] = set(chain.from_iterable(map(lambda x: x.signature, self.nibbles)))
        objects = self.ooi_repository.list_oois_by_object_types(signatures_object_types, datetime.now())
        objects_by_type = {t: {x for x in objects if isinstance(otype(x), t)} for t in set(map(otype, objects))}
        retval = set()
        while stack:
            ooi = stack.pop()
            objects_by_type[otype(ooi)] |= {ooi}
            retval |= self.run(ooi, objects_by_type)

        return retval
