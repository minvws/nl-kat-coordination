from tools.models import Organization

from katalogus.client import Boefje, get_katalogus
from octopoes.models import OOI


def get_enabled_boefjes_for_ooi_class(ooi_class: type[OOI], organization: Organization) -> list[Boefje]:
    katalogus = get_katalogus(organization.code)

    return [boefje for boefje in katalogus.get_enabled_boefjes() if ooi_class in boefje.consumes]
