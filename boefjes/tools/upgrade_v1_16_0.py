#!/usr/bin/env python3

"""Migration script for v1.16.0 due to a bug in the garbage collection. To be removed in later versions."""

import json
import logging.config
import sys
from datetime import datetime, timezone
from pathlib import Path

import click
from httpx import HTTPStatusError
from sqlalchemy.orm import sessionmaker

from boefjes.api import get_bytes_client
from boefjes.config import settings
from boefjes.dependencies.plugins import get_plugin_service, PluginService
from boefjes.job_handler import get_octopoes_api_connector
from boefjes.local_repository import get_local_repository
from boefjes.sql.config_storage import create_config_storage
from boefjes.sql.db import get_engine
from boefjes.sql.organisation_storage import create_organisation_storage
from octopoes.api.models import Affirmation, Declaration, Observation
from octopoes.connector.octopoes import OctopoesAPIConnector
from octopoes.models.origin import Origin, OriginType

from boefjes.sql.plugin_storage import create_plugin_storage

sys.path.append(str(Path(__file__).resolve().parent.parent))


with settings.log_cfg.open() as f:
    logging.config.dictConfig(json.load(f))

logger = logging.getLogger(__name__)


def upgrade(valid_time: datetime | None = None) -> tuple[int, int]:
    """
    Perform the migration for all organisations in the database. The happy flow in this script is idempotent,
    meaning that it can be rerun until there are no, or only expected, exceptions.
    """

    organisations = create_organisation_storage(sessionmaker(bind=get_engine())()).get_all()

    if valid_time is None:
        valid_time = datetime.now(timezone.utc)

    bytes_client = get_bytes_client()
    bytes_client.login()

    total_failed = 0
    total_processed = 0
    logger.info("Processing %s organisations in total", len(organisations))

    for organisation_id in organisations:
        connector = get_octopoes_api_connector(organisation_id)
        logger.info("Processing organisation [organization_id=%s]", organisation_id)

        failed, processed = migrate_org(bytes_client, connector, organisation_id, valid_time)
        total_failed += failed
        total_processed += processed

        logger.info("Processed organisation [total_processed=%s, total_failed=%s]", processed, failed)

    logger.info("Finished migration [total_processed=%s, total_failed=%s]", total_processed, total_failed)

    return total_processed, total_failed


def migrate_org(bytes_client, connector, organisation_id, valid_time) -> tuple[int, int]:
    """
    For each organisation, we paginate through the origin API, find the matching normalizer meta in Bytes,
    and set the source_method to the boefje id. Then update the origin, i.e. save it and delete the old one.
    """

    failed = 0
    processed = 0

    offset = 0
    page_size = 200

    session = sessionmaker(bind=get_engine())()

    all_plugins = PluginService(
        create_plugin_storage(session),
        create_config_storage(session),
        get_local_repository(),
    )._get_all_without_enabled()

    normalizers = {}

    for normalizer in [x for x in all_plugins.values() if x.type == "normalizer"]:
        boefjes = []

        for plugin in all_plugins.values():
            if plugin.type == "boefje" and f"boefje/{plugin.id}" in normalizer.consumes:
                boefjes.append(plugin)

        normalizers[normalizer.id] = boefjes

    while True:
        origins = connector.list_origins(valid_time, method=normalizers.keys(), offset=offset, limit=page_size)
        logger.info("Processing %s origins", len(origins))

        for origin in origins:
            if origin.source_method is not None or origin.origin_type == OriginType.INFERENCE:
                continue

            if origin.method in normalizers and len(normalizers[origin.method]) == 1:
                origin.source_method = normalizers[origin.method][0].id
                update_origin(connector, origin, valid_time)
                continue

            try:
                normalizer_meta = bytes_client.get_normalizer_meta(origin.task_id)
                origin.source_method = normalizer_meta.raw_data.boefje_meta.boefje.id
                update_origin(connector, origin, valid_time)
            except HTTPStatusError as error:
                # We expect to find Declaration/Affirmations without a normalizer meta
                if error.response.status_code == 404 and origin.method != "manual":
                    logger.warning(
                        "Could not find normalizer_meta [task_id=%s, method=%s, origin_type=%s]",
                        origin.task_id,
                        origin.method,
                        origin.origin_type,
                    )
                elif error.response.status_code == 404:
                    logger.info(
                        "Could not find normalizer_meta [task_id=%s, method=%s, origin_type=%s]",
                        origin.task_id,
                        origin.method,
                        origin.origin_type,
                    )
                else:
                    logger.exception(
                        "Could not update origin [task_id=%s, method=%s, origin_type=%s]",
                        origin.task_id,
                        origin.method,
                        origin.origin_type,
                    )
                    failed += 1

                continue

            processed += 1

        if len(origins) < 200:
            logger.info("Processed all origins [organization_id=%s]", organisation_id)
            break

        offset += page_size
        
    session.close()
    return failed, processed


def update_origin(connector: OctopoesAPIConnector, origin: Origin, valid_time) -> None:
    """
    Save the origin as either an observation, declaration or affirmation - depending on the type - and delete the
    old origin.
    """
    if origin.origin_type == OriginType.OBSERVATION:
        # Note that observations need OOITypes in its result, but origins only return a list of references
        result = connector.load_objects_bulk(set(origin.result), valid_time).values()
        connector.save_observation(
            Observation(**origin.model_dump(exclude={"origin_type", "result"}), result=result, valid_time=valid_time)
        )

    if origin.origin_type == OriginType.DECLARATION:
        # Same OOIType vs. Reference issue here
        ooi = connector.get(origin.source, valid_time)
        connector.save_declaration(
            Declaration(
                **origin.model_dump(exclude={"origin_type", "source", "results"}),
                ooi=ooi,
                results=[ooi],
                valid_time=valid_time,
            )
        )

    if origin.origin_type == OriginType.AFFIRMATION:
        # Same OOIType vs. Reference issue here
        ooi = connector.get(origin.source, valid_time)
        connector.save_affirmation(
            Affirmation(
                **origin.model_dump(exclude={"origin_type", "source", "results"}),
                ooi=ooi,
                results=[ooi],
                valid_time=valid_time,
            )
        )

    origin.source_method = None  # This assures the origin.id takes on the old value so we can delete the old entity
    connector.delete_origin(origin.id, valid_time)


@click.command()
def main():
    upgrade()


if __name__ == "__main__":
    main()
