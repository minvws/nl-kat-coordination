import logging
import os
from collections.abc import Iterable

from boefjes.job_models import (
    BoefjeMeta,
    InvalidReturnValueNormalizer,
    NormalizerAffirmation,
    NormalizerDeclaration,
    NormalizerMeta,
    NormalizerObservation,
    NormalizerOutput,
    NormalizerResults,
    ObservationsWithoutInputOOI,
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

        if not boefje_resource.module:
            if boefje_resource.boefje.oci_image:
                raise JobRuntimeError("Trying to run OCI image boefje locally")
            else:
                raise JobRuntimeError("Boefje doesn't have OCI image or main.py")

        with TemporaryEnvironment() as temporary_environment:
            temporary_environment.update(environment)
            try:
                return boefje_resource.module.run(boefje_meta)
            except BaseException as e:  # noqa
                raise JobRuntimeError("Boefje failed") from e


class LocalNormalizerJobRunner(NormalizerJobRunner):
    def __init__(self, local_repository: LocalPluginRepository):
        self.local_repository = local_repository

    def run(self, normalizer_meta: NormalizerMeta, raw: bytes) -> NormalizerResults:
        logger.debug("Running local normalizer plugin")

        normalizers = self.local_repository.resolve_normalizers()
        normalizer = normalizers[normalizer_meta.normalizer.id]

        try:
            try:
                input_ooi = normalizer_meta.raw_data.boefje_meta.arguments["input"]
            except KeyError:
                if normalizer_meta.raw_data.boefje_meta.input_ooi:
                    input_ooi = {"primary_key": normalizer_meta.raw_data.boefje_meta.input_ooi}
                else:
                    input_ooi = {}

            results = normalizer.module.run(input_ooi, raw)
        except BaseException as e:
            raise JobRuntimeError("Normalizer failed") from e

        return self._parse_results(normalizer_meta, results)

    def _parse_results(self, normalizer_meta: NormalizerMeta, results: Iterable[NormalizerOutput]) -> NormalizerResults:
        oois = []
        declarations = []
        affirmations = []
        scan_profiles = []

        for result in results:
            match result:
                case OOI():
                    oois.append(result)
                case NormalizerDeclaration():
                    declarations.append(result)
                case NormalizerAffirmation():
                    affirmations.append(result)
                case DeclaredScanProfile():
                    scan_profiles.append(result)
                case _:
                    raise InvalidReturnValueNormalizer(
                        f"Normalizer returned object of incorrect type: {result.__class__.__name__}"
                    )

        if oois:
            if not normalizer_meta.raw_data.boefje_meta.input_ooi:
                raise ObservationsWithoutInputOOI(normalizer_meta)

            observations = [
                NormalizerObservation(
                    type="observation",
                    input_ooi=normalizer_meta.raw_data.boefje_meta.input_ooi,
                    results=oois,
                )
            ]
        else:
            observations = []

        return NormalizerResults(
            observations=observations,
            declarations=declarations,
            affirmations=affirmations,
            scan_profiles=scan_profiles,
        )
