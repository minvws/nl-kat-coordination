import logging
import os
from typing import Any

from pydantic import ValidationError

from boefjes.job_models import (
    BoefjeMeta,
    InvalidReturnValueNormalizer,
    NormalizerAffirmation,
    NormalizerDeclaration,
    NormalizerMeta,
    NormalizerObservation,
    NormalizerOutput,
    NormalizerPlainOOI,
    NormalizerResult,
    NormalizerScanProfile,
    ObservationsWithoutInputOOI,
    UnsupportedReturnTypeNormalizer,
)
from boefjes.katalogus.local_repository import LocalPluginRepository
from boefjes.runtime_interfaces import BoefjeJobRunner, JobRuntimeError, NormalizerJobRunner
from octopoes.models import OOI, DeclaredScanProfile

logger = logging.getLogger(__name__)


class TemporaryEnvironment:
    """Context manager that temporarily clears the environment vars and restores it after exiting the context"""

    def __init__(self):
        self._original_environment = os.environ.copy()

    def __enter__(self):
        os.environ.clear()
        return os.environ

    def __exit__(self, exc_type, exc_val, exc_tb):
        os.environ.clear()
        os.environ.update(self._original_environment)


class LocalBoefjeJobRunner(BoefjeJobRunner):
    def __init__(self, local_repository: LocalPluginRepository):
        self.local_repository = local_repository

    def run(self, boefje_meta: BoefjeMeta, environment: dict[str, str]) -> list[tuple[set, bytes | str]]:
        logger.debug("Running local boefje plugin")

        boefjes = self.local_repository.resolve_boefjes()
        boefje_resource = boefjes[boefje_meta.boefje.id]

        if not boefje_resource.module and boefje_resource.boefje.oci_image:
            raise JobRuntimeError("Trying to run OCI image boefje locally")

        with TemporaryEnvironment() as temporary_environment:
            temporary_environment.update(environment)
            try:
                return boefje_resource.module.run(boefje_meta)
            except BaseException as e:  # noqa
                raise JobRuntimeError("Boefje failed") from e


class LocalNormalizerJobRunner(NormalizerJobRunner):
    def __init__(self, local_repository: LocalPluginRepository):
        self.local_repository = local_repository

    def run(self, normalizer_meta, raw) -> NormalizerOutput:
        logger.debug("Running local normalizer plugin")

        normalizers = self.local_repository.resolve_normalizers()
        normalizer = normalizers[normalizer_meta.normalizer.id]

        try:
            results = normalizer.module.run(normalizer_meta, raw)
        except BaseException as e:
            raise JobRuntimeError("Normalizer failed") from e

        return self._parse_results(normalizer_meta, results)

    def _parse_results(self, normalizer_meta: NormalizerMeta, results: list[Any]) -> NormalizerOutput:
        parsed: list[NormalizerResult] = [self._parse(result) for result in results]

        if oois := [ooi for ooi in parsed if isinstance(ooi.item, NormalizerPlainOOI)]:
            if not normalizer_meta.raw_data.boefje_meta.input_ooi:
                raise ObservationsWithoutInputOOI(normalizer_meta)

            # For both compatibility and ease of use, this makes sure we support normalizers only returning OOI dicts.
            parsed.append(
                NormalizerResult(
                    item=NormalizerObservation(
                        type="observation",
                        input_ooi=normalizer_meta.raw_data.boefje_meta.input_ooi,
                        results=[result.item for result in oois],
                    )
                )
            )

        observations = [result.item for result in parsed if isinstance(result.item, NormalizerObservation)]

        if observations and not normalizer_meta.raw_data.boefje_meta.input_ooi:
            raise ObservationsWithoutInputOOI(normalizer_meta)

        return NormalizerOutput(
            observations=observations,
            declarations=[result.item for result in parsed if isinstance(result.item, NormalizerDeclaration)],
            affirmations=[result.item for result in parsed if isinstance(result.item, NormalizerAffirmation)],
            scan_profiles=[result.item for result in parsed if isinstance(result.item, NormalizerScanProfile)],
        )

    @staticmethod
    def _parse(result: Any) -> NormalizerResult:
        if not isinstance(result, dict):  # Must be an OOI or ScanProfile. Should be phased out with Octopoes dependency
            if not isinstance(result, OOI | DeclaredScanProfile):
                raise UnsupportedReturnTypeNormalizer(str(type(result)))

            result = result.dict()

        try:
            return NormalizerResult(item=result)
        except ValidationError as e:
            raise InvalidReturnValueNormalizer(e.json())
