from pathlib import Path

import logging
from datetime import datetime, timezone
import os
from typing import Union, Tuple, List, Dict

import pydantic
import requests

from octopoes.models import OOI

from boefjes.plugins.models import BoefjeResource, NormalizerResource, RawData
from boefjes.config import settings
from boefjes.job_models import BoefjeMeta, NormalizerMeta
from boefjes.katalogus.models import PluginType

logger = logging.getLogger(__name__)


class TemporaryEnvironment:
    def __init__(self):
        self._original_environment = os.environ.copy()

    def __enter__(self):
        return os.environ

    def __exit__(self, exc_type, exc_val, exc_tb):
        os.environ = self._original_environment


def get_environment_settings(
    boefje_meta: BoefjeMeta, environment_keys: List[str]
) -> Dict[str, str]:
    environment = requests.get(
        f"{settings.katalogus_api}/v1/organisations/{boefje_meta.organization}/{boefje_meta.boefje.id}/settings"
    ).json()

    return {k: v for k, v in environment.items() if k in environment_keys}


def get_plugin(
    organisation: str, repository: str, plugin_id: str, version: str
) -> PluginType:
    res = requests.get(
        f"{settings.katalogus_api}/v1/organisations/{organisation}/repositories/{repository}/plugins/{plugin_id}:{version}"
    )

    return pydantic.parse_raw_as(PluginType, res.content)


class BoefjeJobRunner:
    def run(self) -> Tuple[BoefjeMeta, RawData]:
        raise NotImplementedError()


class LocalBoefjeJobRunner(BoefjeJobRunner):
    def __init__(
        self,
        boefje_meta: BoefjeMeta,
        boefje: BoefjeResource,
        extra_environment: Dict[str, str],
    ):
        self.boefje_meta = boefje_meta
        self.boefje_resource = boefje
        self.environment = extra_environment

    def run(self) -> Tuple[BoefjeMeta, RawData]:
        self.boefje_meta.started_at = datetime.now(timezone.utc)

        try:
            with TemporaryEnvironment() as temporary_environment:
                temporary_environment.update(self.environment)
                self.boefje_meta, output = self.boefje_resource.module.run(
                    self.boefje_meta
                )

        except Exception as exc:
            logger.exception(
                "Error while running boefje module %s[%s]",
                self.boefje_meta.boefje.id,
                self.boefje_meta.id,
                exc_info=True,
            )
            raise exc

        finally:
            self.boefje_meta.ended_at = datetime.now(timezone.utc)

        return self.boefje_meta, RawData(
            data=output, mime_types={self.boefje_meta.boefje.id}
        )

    def __str__(self):
        return f"BoefjeJobRunner {self.boefje_meta.id}"


class NormalizerJobRunner:
    def __init__(
        self,
        normalizer_meta: NormalizerMeta,
        normalizer: NormalizerResource,
        raw: Union[str, bytes],
    ):
        self.normalizer_meta = normalizer_meta
        self.normalizer = normalizer

        self.raw = raw
        self.results: List[OOI] = []

    def run(self):
        self.normalizer_meta.started_at = datetime.now(timezone.utc)

        try:
            self.results = list(
                self.normalizer.module.run(self.normalizer_meta, self.raw)
            )
        except Exception as exc:
            logger.exception(f"Normalizer {self.normalizer_meta=} failed")
            raise exc

        # Do not add the input OOI to the results to properly handle deletion propagation.
        input_ooi = self.normalizer_meta.boefje_meta.input_ooi
        self.results = list(filter(lambda r: r.reference != input_ooi, self.results))

        self.normalizer_meta.ended_at = datetime.now(timezone.utc)

    def __str__(self):
        return f"NormalizerJobRunner {self.normalizer_meta.id}"
