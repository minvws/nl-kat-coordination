from datetime import datetime, timedelta, timezone
from typing import Iterable, Union

from boefjes.config import settings
from boefjes.job_models import NormalizerMeta
from octopoes.connector.octopoes import ObjectNotFoundException, OctopoesAPIConnector
from octopoes.models import OOI, Reference
from octopoes.models.ooi.findings import Finding, KATFindingType
from octopoes.models.ooi.network import IPPort


def run(normalizer_meta: NormalizerMeta, raw: Union[bytes, str]) -> Iterable[OOI]:
    boefje_meta = normalizer_meta.raw_data.boefje_meta
    ooi = Reference.from_str(boefje_meta.input_ooi)

    connector = OctopoesAPIConnector(settings.octopoes_api, boefje_meta.organization)

    # Get current ports
    try:
        current_tree = connector.get_tree(ooi, types={IPPort}, depth=1)
    except ObjectNotFoundException:
        # This IP doesn't exist anymore
        return

    current_ports = set()
    for primary_key, ooi in current_tree.store.items():
        if isinstance(ooi, IPPort):
            current_ports.add(ooi.port)

    # Get ports from a week ago
    last_week = datetime.now(timezone.utc) - timedelta(days=7)
    try:
        old_tree = connector.get_tree(ooi, types={IPPort}, depth=1, valid_time=last_week)
    except ObjectNotFoundException:
        # This IP was not known a week ago
        return

    week_old_ports = set()
    for primary_key, ooi in old_tree.store.items():
        if isinstance(ooi, IPPort):
            week_old_ports.add(ooi.port)

    # Get number of different ports
    num_new_ports = 0
    for port in current_ports:
        if port not in week_old_ports:
            num_new_ports += 1

    # Make Finding if too many ports are opened last week
    if num_new_ports > 10:
        kat_ooi = KATFindingType(id="KAT-10-OR-MORE-NEW-PORTS-OPEN")
        yield kat_ooi
        yield Finding(
            finding_type=kat_ooi.reference,
            ooi=ooi,
            description=f"There are {num_new_ports} ports open that were not open last week.",
        )
