import logging
from datetime import datetime, timezone
from importlib import import_module
from inspect import signature, Signature, isfunction
from typing import Union, Any, Tuple, Iterator, List, Protocol, cast, Dict

from octopoes.models import OOI

from boefjes.models import Boefje, Normalizer, RawData
from job import BoefjeMeta, NormalizerMeta

logger = logging.getLogger(__name__)


class ModuleException(Exception):
    """General error for modules"""


class BoefjeJobRunner:
    def run(self) -> Tuple[BoefjeMeta, RawData]:
        raise NotImplementedError()


class LocalBoefjeJobRunner(BoefjeJobRunner):
    def __init__(self, boefje_meta: BoefjeMeta, boefje: Boefje, boefje_dir: str):
        self.boefje_meta = boefje_meta
        self.boefje = boefje
        self.boefje_dir = boefje_dir

    def run(self) -> Tuple[BoefjeMeta, RawData]:
        self.boefje_meta.started_at = datetime.now(timezone.utc)
        self.boefje_meta, raw = self.run_boefje_version()
        self.boefje_meta.ended_at = datetime.now(timezone.utc)

        return self.boefje_meta, RawData(data=raw, mime_types={self.boefje.id})

    def run_boefje_version(self):
        module_runner = ModuleRunner(
            f"{self.boefje_dir}.{self.boefje.module}", OLD_BOEFJE_SIGNATURE
        )

        return module_runner.run(self.boefje_meta)

    def __str__(self):
        return f"BoefjeJobRunner {self.boefje_meta.id}"


class NormalizerJobRunner:
    def __init__(
        self,
        normalizer_meta: NormalizerMeta,
        normalizer: Normalizer,
        boefje_dir: str,
        raw: Union[str, bytes],
    ):
        self.normalizer_meta = normalizer_meta
        self.normalizer = normalizer
        self.boefje_dir = boefje_dir

        self.raw = raw
        self.results: List[OOI] = []
        self._module_runner = ModuleRunner(
            f"{self.boefje_dir}.{self.normalizer.module}", NORMALIZER_SIGNATURE
        )

    def run(self):
        self.normalizer_meta.started_at = datetime.now(timezone.utc)
        self.results = list(self._module_runner.run(self.normalizer_meta, self.raw))

        # Do not add the input OOI to the results to properly handle deletion propagation.
        input_ooi = self.normalizer_meta.boefje_meta.input_ooi
        self.results = list(filter(lambda r: r.reference != input_ooi, self.results))

        self.normalizer_meta.ended_at = datetime.now(timezone.utc)

    def __str__(self):
        return f"NormalizerJobRunner {self.normalizer_meta.id}"


class Runnable(Protocol):
    def run(self, *args, **kwargs) -> Any:
        ...


class ModuleRunner:
    def __init__(self, module: str, sign: Signature):
        self.module = module
        self.signature = sign

    def run(self, *args, **kwargs) -> Any:
        module = import_module(self.module)
        module = cast(Runnable, module)

        if not hasattr(module, "run") or not isfunction(module.run):
            raise ModuleException(f"Module {module} does not define a run function")

        if signature(module.run).return_annotation != self.signature.return_annotation:
            raise ModuleException(
                f"Invalid run function return ann   otation, expected '{self.signature.return_annotation}'"
            )

        return module.run(*args, **kwargs)


def _old_boefje_run_signature(
    boefje_meta: BoefjeMeta,
) -> Tuple[BoefjeMeta, Union[str, bytes]]:
    pass


def _boefje_run_signature(
    _: Dict,
) -> Union[str, bytes]:
    pass


def _normalizer_run_signature(
    normalizer_meta: NormalizerMeta, raw: Union[bytes, str]
) -> Iterator[OOI]:
    pass


NORMALIZER_SIGNATURE = signature(_normalizer_run_signature)
OLD_BOEFJE_SIGNATURE = signature(_old_boefje_run_signature)
NEW_BOEFJE_SIGNATURE = signature(_boefje_run_signature)
