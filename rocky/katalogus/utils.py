from typing import Type, List

from katalogus.client import get_katalogus, Plugin
from octopoes.models import OOI
from tools.models import Organization


def get_enabled_boefjes_for_ooi_class(ooi_class: Type[OOI], organization: Organization) -> List[Plugin]:
    return [boefje for boefje in get_katalogus(organization.code).get_enabled_boefjes() if ooi_class in boefje.consumes]
