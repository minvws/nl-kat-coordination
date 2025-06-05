import time
import timeit
from datetime import datetime, timezone
from logging import config
from pathlib import Path

import structlog
import yaml

from httpx import HTTPError

from octopoes.core.app import bootstrap_octopoes, get_xtdb_client
from octopoes.config.settings import Settings
from octopoes.connector.katalogus import KATalogusClient
from octopoes.xtdb.client import XTDBSession

RECALCULATE_INTERVAL = 60

settings = Settings()
logger = structlog.get_logger(__name__)

try:
    with Path(settings.log_cfg).open() as log_config:
        config.dictConfig(yaml.safe_load(log_config))
        logger.info("Configured loggers with config: %s", settings.log_cfg)
except FileNotFoundError:
    logger.warning("No log config found at: %s", settings.log_cfg)

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper("iso", utc=False),
        (
            structlog.dev.ConsoleRenderer(colors=True, pad_level=False)
            if settings.logging_format == "text"
            else structlog.processors.JSONRenderer()
        ),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

def scan_profile_recalculations(katalogusclient: KATalogusClient, octopii: dict) -> None:
    try:
        orgs = katalogusclient.get_organisations()
    except HTTPError:
        logger.exception("Failed getting organizations from KATalogus")
        raise
    for org in orgs:
        if org not in octopii.keys():
            xtdb_session = XTDBSession(get_xtdb_client(str(settings.xtdb_uri), org))
            octopoes = bootstrap_octopoes(settings, org, xtdb_session)
            octopii[org] = {"octopoes": octopoes,
                            "xtdb": xtdb_session,
                            "last_transaction": 0,
                            "org": org}
        last_transaction = recalculate_scan_profiles_for_org(octopii[org])
        if last_transaction:
            octopii[org]["last_transaction"] = last_transaction


def recalculate_scan_profiles_for_org(session: dict) -> int | None:
    timer = timeit.default_timer()
    max_id = session["xtdb"].client.latest_completed_tx()
    if max_id and session["last_transaction"] == max_id["txId"]:
        logger.info("skipping scan profile recalculation task, no new transactions present, last transaction: %i [org=%s]", max_id["txId"], session["org"])
        return
    else:
        logger.info("Most recent worked transactions %i, most recent %i [org=%s] ", session["last_transaction"], max_id["txId"],  session["org"],)

    try:
        session["octopoes"].recalculate_scan_profiles(datetime.now(timezone.utc))
        session["xtdb"].commit()
        logger.info("Finished scan profile recalculation [org=%s] [dur=%.2fs]", session["org"], timeit.default_timer() - timer)
        return max_id["txId"]
    except Exception:
        logger.exception("Failed recalculating scan profiles [org=%s] [dur=%.2fs]", session["org"], timeit.default_timer() - timer)
    return None

def main():
    logger.info("Scan profile recalculation thread started.")
    katalogusclient = KATalogusClient(str(settings.katalogus_api))
    octopii = {}
    while True:        
        scan_profile_recalculations(katalogusclient, octopii)
        time.sleep(RECALCULATE_INTERVAL)
        
if __name__ == "__main__":
    main()
