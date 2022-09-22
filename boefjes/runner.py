import logging
from datetime import datetime, timezone
from importlib import import_module
from inspect import signature, Signature, isfunction
import os
from typing import Union, Any, Tuple, Iterator, List, Protocol, cast, Dict, Optional

import pydantic
import requests
from octopoes.models import OOI

from boefjes.plugins.models import Boefje, Normalizer, RawData
from boefjes.config import settings
from boefjes.job import BoefjeMeta, NormalizerMeta
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
    boefje_meta: BoefjeMeta, boefje_resource: Boefje
) -> Dict[str, str]:
    environment = requests.get(
        f"{settings.katalogus_api}/v1/organisations/{boefje_meta.organization}/{boefje_meta.boefje.id}/settings"
    ).json()

    return {
        k: v for k, v in environment.items() if k in boefje_resource.environment_keys
    }


def get_plugin(
    organisation: str, repository: str, plugin_id: str, version: str
) -> PluginType:
    res = requests.get(
        f"{settings.katalogus_api}/v1/organisations/{organisation}/repositories/{repository}/plugins/{plugin_id}:{version}"
    )

    return pydantic.parse_raw_as(PluginType, res.content)


class ModuleException(Exception):
    """General error for modules"""


class BoefjeJobRunner:
    def run(self) -> Tuple[BoefjeMeta, RawData]:
        raise NotImplementedError()


class LocalBoefjeJobRunner(BoefjeJobRunner):
    def __init__(
        self,
        boefje_meta: BoefjeMeta,
        boefje: Boefje,
        extra_environment: Dict[str, str],
    ):
        self.boefje_meta = boefje_meta
        self.boefje = boefje
        self.environment = extra_environment

    def run(self) -> Tuple[BoefjeMeta, RawData]:
        self.boefje_meta.started_at = datetime.now(timezone.utc)

        try:
            module_runner = ModuleRunner(
                self.boefje.module,
                OLD_BOEFJE_SIGNATURE,
                self.environment,
            )

            self.boefje_meta, output = module_runner.run(self.boefje_meta)

        except Exception as exc:
            logger.exception(
                "Error while running boefje module %s[%s]",
                self.boefje.id,
                self.boefje_meta.id,
                exc_info=True,
            )
            raise exc

        finally:
            self.boefje_meta.ended_at = datetime.now(timezone.utc)

        return self.boefje_meta, RawData(data=output, mime_types={self.boefje.id})

    def __str__(self):
        return f"BoefjeJobRunner {self.boefje_meta.id}"


class NormalizerJobRunner:
    def __init__(
        self,
        normalizer_meta: NormalizerMeta,
        normalizer: Normalizer,
        raw: Union[str, bytes],
    ):
        self.normalizer_meta = normalizer_meta
        self.normalizer = normalizer

        self.raw = raw
        self.results: List[OOI] = []
        self._module_runner = ModuleRunner(
            self.normalizer.module, NORMALIZER_SIGNATURE, {}
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
    def __init__(self, module: str, sign: Signature, environment: Dict[str, str]):
        self.module = module
        self.signature = sign
        self.environment = environment

    def run(self, *args, **kwargs) -> Any:
        module = import_module(self.module)
        module = cast(Runnable, module)

        if not hasattr(module, "run") or not isfunction(module.run):
            raise ModuleException(f"Module {module} does not define a run function")

        if signature(module.run).return_annotation != self.signature.return_annotation:
            raise ModuleException(
                f"Invalid run function return ann   otation, expected '{self.signature.return_annotation}'"
            )

        with TemporaryEnvironment() as temporary_environment:
            temporary_environment.update(self.environment)
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
