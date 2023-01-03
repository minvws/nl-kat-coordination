import logging
import os
from typing import List, Dict, Union, Tuple

from octopoes.models import OOI

from boefjes.job_models import BoefjeMeta
from boefjes.katalogus.local_repository import LocalPluginRepository
from boefjes.runtime_interfaces import BoefjeJobRunner, NormalizerJobRunner

logger = logging.getLogger(__name__)


class TemporaryEnvironment:
    def __init__(self):
        self._original_environment = os.environ.copy()

    def __enter__(self):
        return os.environ

    def __exit__(self, exc_type, exc_val, exc_tb):
        os.environ = self._original_environment


class LocalBoefjeJobRunner(BoefjeJobRunner):
    def __init__(self, local_repository: LocalPluginRepository):
        self.local_repository = local_repository

    def run(self, boefje_meta: BoefjeMeta, environment: Dict[str, str]) -> List[Tuple[set, Union[bytes, str]]]:
        logger.info("Running local boefje plugin")

        boefjes = self.local_repository.resolve_boefjes()
        boefje_resource = boefjes[boefje_meta.boefje.id]

        with TemporaryEnvironment() as temporary_environment:
            temporary_environment.update(environment)
            return boefje_resource.module.run(boefje_meta)


class LocalNormalizerJobRunner(NormalizerJobRunner):
    def __init__(self, local_repository: LocalPluginRepository):
        self.local_repository = local_repository

    def run(self, normalizer_meta, raw) -> List[OOI]:
        logger.info("Running local normalizer plugin")

        normalizers = self.local_repository.resolve_normalizers()
        normalizer = normalizers[normalizer_meta.normalizer.id]

        return list(normalizer.module.run(normalizer_meta, raw))
