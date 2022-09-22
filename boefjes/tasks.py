import logging
from typing import Dict, List

import pydantic
import requests

from boefjes.app import app
from boefjes.config import settings
from boefjes.job import BoefjeMeta, NormalizerMeta
from boefjes.job_handler import (
    handle_boefje_meta,
    handle_normalizer_meta,
)
from boefjes.katalogus.models import PluginType

logger = logging.getLogger(__name__)


def get_all_plugins(organisation: str) -> List[PluginType]:
    res = requests.get(
        f"{settings.katalogus_api}/v1/organisations/{organisation}/plugins"
    )

    return pydantic.parse_raw_as(List[PluginType], res.content)


@app.task(queue="boefjes", name="tasks.handle_boefje")
def handle_boefje(job: Dict) -> Dict:
    boefje_meta = BoefjeMeta(**job)

    return handle_boefje_meta(boefje_meta)


@app.task(queue="normalizers", name="tasks.handle_normalizer")
def handle_normalizer(normalizer_job: Dict) -> None:
    data = normalizer_job.copy()
    boefje_meta = BoefjeMeta(**data.pop("boefje_meta"))
    normalizer_meta = NormalizerMeta(boefje_meta=boefje_meta, **data)

    handle_normalizer_meta(normalizer_meta)
