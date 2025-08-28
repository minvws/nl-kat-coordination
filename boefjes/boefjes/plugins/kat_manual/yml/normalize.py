import io
import logging
from collections.abc import Iterable
from typing import Any, TypedDict
from typing_extensions import NotRequired

import yaml
from pydantic import ValidationError

from boefjes.normalizer_models import NormalizerDeclaration, NormalizerOutput
from octopoes.models import OOI, Reference
from octopoes.models.types import OOI_TYPES as CONCRETE_OOI_TYPES
from octopoes.models.ooi.findings import Finding, FindingType
from octopoes.models.ooi.certificate import SubjectAlternativeName
from octopoes.models.ooi.dns.records import DNSRecord
from octopoes.models.ooi.geography import GeographicPoint
from octopoes.models.ooi.network import NetBlock, Network
from octopoes.models.ooi.web import IPAddress, WebURL


class OOITypeEntry(TypedDict):
    type: type[OOI]
    distinctive_fields: NotRequired[list[str]]


OOI_TYPES: dict[str, OOITypeEntry] = {
    ooi_type: {"type": CONCRETE_OOI_TYPES[ooi_type]} for ooi_type in CONCRETE_OOI_TYPES
}
# Types without _natural_key_attrs
OOI_TYPES["GeographicPoint"] = {"type": GeographicPoint, "distinctive_fields": ["ooi", "longitude", "latitude"]}
OOI_TYPES["Finding"] = {"type": Finding, "distinctive_fields": ["ooi", "finding_type"]}
OOI_TYPES["WebURL"] = {"type": WebURL, "distinctive_fields": ["scheme", "port", "path"]}
OOI_TYPES["SubjectAlternativeName"] = {"type": SubjectAlternativeName}
OOI_TYPES["FindingType"] = {"type": FindingType}
OOI_TYPES["IPAddress"] = {"type": IPAddress}
OOI_TYPES["NetBlock"] = {"type": NetBlock}
OOI_TYPES["DNSRecord"] = {"type": DNSRecord}


logger = logging.getLogger(__name__)


def run(input_ooi: dict, raw: bytes) -> Iterable[NormalizerOutput]:
    reference_cache = {"Network": {"internet": Network(name="internet")}}

    yield from process_yml(raw, reference_cache)


def process_yml(yml_raw_data: bytes, reference_cache: dict) -> Iterable[NormalizerOutput]:
    yml_data = io.StringIO(yml_raw_data.decode())
    oois_from_yaml = yaml.safe_load(yml_data)
    oois: list[NormalizerOutput] = []
    for ooi_number, ooi_dict in enumerate(oois_from_yaml):
        try:
            create_oois(ooi_dict, reference_cache, oois)
        except ValidationError as err:
            logger.exception("Validation failed for indexed object at %s, with error: %s", ooi_number, str(err))
    return oois


def create_oois(ooi_dict: dict, reference_cache: dict, oois_list: list):
    # constants
    skip_properties = ("object_type", "scan_profile", "primary_key", "user_id")
    # check for main ooi
    ooi_type = OOI_TYPES[ooi_dict["ooi_type"]]["type"]
    # Special Cases
    ooi_type = ooi_type.type_from_raw(ooi_dict)
    # check for cache
    cache, cache_field_name = get_cache_and_field_name(ooi_type, ooi_dict, reference_cache)
    if cache_field_name in cache:
        return cache[cache_field_name]
    # creation process
    ooi_fields = [
        (
            field,
            field if model_field.annotation != Reference else model_field.json_schema_extra["object_type"],
            model_field.annotation == Reference,
            model_field.is_required(),
        )
        for field, model_field in ooi_type.__fields__.items()
        if field not in skip_properties
    ]
    kwargs: dict[str, Any] = {}
    for field, referenced_type, is_reference, required in ooi_fields:
        # required referenced fields or not required but also defined in yaml
        if is_reference and required or is_reference and ooi_dict.get(field):
            try:
                new_ooi = ooi_dict.get(field.lower()) or ooi_dict.get(referenced_type.lower())
                if new_ooi is not None:
                    referenced_ooi = create_oois(new_ooi, reference_cache, oois_list)
                    kwargs[field] = referenced_ooi.reference
            except IndexError:
                if required:
                    raise IndexError(
                        f"Required referenced primary-key field '{field}' not set "
                        f"and no default present for Type '{ooi_type.__name__}'."
                    )
                else:
                    kwargs[field] = None
        # not required and not defined referenced field still in loop. they skipped with "not is_reference"
        # required fields or not required but also defined in yaml
        elif not is_reference and (required or not required and ooi_dict.get(field)):
            kwargs[field] = ooi_dict.get(field)
    ooi = ooi_type(**kwargs)
    # Save to cache
    cache[cache_field_name] = ooi
    oois_list.append(NormalizerDeclaration(ooi=ooi))
    return ooi


def get_cache_and_field_name(ooi_type: type[OOI], ooi_dict: dict, reference_cache: dict) -> tuple[dict[str, OOI], str]:
    dins_fields = OOI_TYPES[ooi_type.__name__].get("distinctive_fields", ooi_type._natural_key_attrs)
    cache_field_name = get_cache_name(ooi_dict, dins_fields)
    cache: dict[str, OOI] = reference_cache.setdefault(ooi_type.object_type, {})
    return cache, cache_field_name


def get_cache_name(ooi_dict: dict, field_combination: list[str]) -> str:
    """It creates name for cache from str values of distinctive fields"""
    return "|".join(filter(None, map(lambda key: str(ooi_dict.get(key, "")), field_combination)))
