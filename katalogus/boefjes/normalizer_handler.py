from collections.abc import Iterable
from datetime import datetime, timezone
from typing import cast

import structlog

from files.models import File
from katalogus.boefjes.models import (
    NormalizerAffirmation,
    NormalizerDeclaration,
    NormalizerObservation,
    NormalizerOutput,
    NormalizerResults,
)
from katalogus.worker.interfaces import JobRuntimeError, NormalizerHandlerInterface
from katalogus.worker.job_models import InvalidReturnValueNormalizer, NormalizerMeta, ObservationsWithoutInputOOI
from katalogus.worker.repository import LocalPluginRepository
from octopoes.api.models import Affirmation, Declaration, Observation
from octopoes.connector.octopoes import OctopoesAPIConnector
from octopoes.models import OOI, DeclaredScanProfile, Reference, ScanLevel
from tasks.models import Task

MIMETYPE_MIN_LENGTH = 5  # two chars before, and 2 chars after the slash ought to be reasonable

logger = structlog.get_logger(__name__)


class LocalNormalizerHandler(NormalizerHandlerInterface):
    def __init__(
        self,
        local_repository: LocalPluginRepository,
        connector: OctopoesAPIConnector,
        whitelist: dict[str, int] | None = None,
    ):
        self.local_repository = local_repository
        self.connector = connector
        self.whitelist = whitelist or {}

    def handle(self, task: Task):
        task.data["started_at"] = str(datetime.now(timezone.utc))
        normalizer_meta = NormalizerMeta.model_validate(task.data)

        logger.info("Handling normalizer %s[%s]", normalizer_meta.normalizer.id, normalizer_meta.id)

        raw = File.objects.get(id=normalizer_meta.raw_data.id)

        try:
            normalizers = self.local_repository.resolve_normalizers()
            normalizer = normalizers[normalizer_meta.normalizer.plugin_id]

            if not normalizer_meta.raw_data.boefje_meta.started_at:
                raise ValueError("Boefje meta has not started_at set")

            if normalizer_meta.raw_data.boefje_meta.input_ooi:
                input_ooi = self.connector.get(
                    normalizer_meta.raw_data.boefje_meta.input_ooi, normalizer_meta.raw_data.boefje_meta.started_at
                ).serialize()
            else:
                input_ooi = {}

            try:
                results = normalizer.module().run(input_ooi, raw.file.read())
            except BaseException as e:
                raise JobRuntimeError("Normalizer failed") from e

            results = self._parse_results(normalizer_meta, results)

            for observation in results.observations:
                for ooi in observation.results:
                    if ooi.primary_key == observation.input_ooi:
                        logger.warning(
                            'Normalizer "%s" returned input [%s]',
                            normalizer_meta.normalizer.plugin_id,
                            observation.input_ooi,
                        )
                reference = Reference.from_str(observation.input_ooi)
                self.connector.save_observation(
                    Observation(
                        method=normalizer_meta.normalizer.plugin_id,
                        source=reference,
                        source_method=normalizer_meta.raw_data.boefje_meta.boefje.plugin_id,
                        task_id=normalizer_meta.id,
                        valid_time=normalizer_meta.raw_data.boefje_meta.ended_at,
                        result=[ooi for ooi in observation.results if ooi.primary_key != observation.input_ooi],
                    )
                )

            for declaration in results.declarations:
                self.connector.save_declaration(
                    Declaration(
                        method=normalizer_meta.normalizer.plugin_id,
                        source_method=normalizer_meta.raw_data.boefje_meta.boefje.plugin_id,
                        ooi=declaration.ooi,
                        task_id=normalizer_meta.id,
                        valid_time=normalizer_meta.raw_data.boefje_meta.ended_at,
                    )
                )

            for affirmation in results.affirmations:
                self.connector.save_affirmation(
                    Affirmation(
                        method=normalizer_meta.normalizer.plugin_id,
                        source_method=normalizer_meta.raw_data.boefje_meta.boefje.plugin_id,
                        ooi=affirmation.ooi,
                        task_id=normalizer_meta.id,
                        valid_time=normalizer_meta.raw_data.boefje_meta.ended_at,
                    )
                )

            if (
                normalizer_meta.raw_data.boefje_meta.input_ooi  # No input OOI means no deletion propagation
                and not (results.observations or results.declarations or results.affirmations)
            ):
                # There were no results found, which we still need to signal to Octopoes for deletion propagation

                self.connector.save_observation(
                    Observation(
                        method=normalizer_meta.normalizer.plugin_id,
                        source=Reference.from_str(normalizer_meta.raw_data.boefje_meta.input_ooi),
                        source_method=normalizer_meta.raw_data.boefje_meta.boefje.plugin_id,
                        task_id=normalizer_meta.id,
                        valid_time=normalizer_meta.raw_data.boefje_meta.ended_at,
                        result=[],
                    )
                )

            corrected_scan_profiles = []
            for profile in results.scan_profiles:
                profile.level = ScanLevel(
                    min(profile.level, self.whitelist.get(normalizer_meta.normalizer.plugin_id, profile.level))
                )
                corrected_scan_profiles.append(profile)

            validated_scan_profiles = [
                profile
                for profile in corrected_scan_profiles
                if self.whitelist and profile.level <= self.whitelist.get(normalizer_meta.normalizer.plugin_id, -1)
            ]
            if validated_scan_profiles:
                self.connector.save_many_scan_profiles(
                    results.scan_profiles,
                    # Mypy doesn't seem to be able to figure out that ended_at is a datetime
                    valid_time=cast(datetime, normalizer_meta.raw_data.boefje_meta.ended_at),
                )
        finally:
            task.data["ended_at"] = str(datetime.now(timezone.utc))
            task.save()
            logger.info("Done with normalizer %s[%s]", normalizer_meta.normalizer.plugin_id, normalizer_meta.id)

    @staticmethod
    def _parse_results(normalizer_meta: NormalizerMeta, results: Iterable[NormalizerOutput]) -> NormalizerResults:
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
                    type="observation", input_ooi=normalizer_meta.raw_data.boefje_meta.input_ooi, results=oois
                )
            ]
        else:
            observations = []

        return NormalizerResults(
            observations=observations, declarations=declarations, affirmations=affirmations, scan_profiles=scan_profiles
        )
