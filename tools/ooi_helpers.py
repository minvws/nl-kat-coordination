from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Optional, Any, Union, TypedDict, Tuple
from octopoes.api.models import Declaration
from octopoes.connector.octopoes import OctopoesAPIConnector
from octopoes.models import OOI
from octopoes.models.exception import ObjectNotFoundException
from octopoes.models.ooi.findings import (
    Finding,
    FindingType,
    KATFindingType,
    CVEFindingType,
    CWEFindingType,
    RetireJSFindingType,
    SnykFindingType,
)
from octopoes.models.tree import ReferenceNode
from octopoes.models.types import get_relations, OOI_TYPES
from pydantic import parse_obj_as
from django.contrib.auth import get_user_model
from tools.models import OOIInformation

User = get_user_model()

RISK_LEVEL_SCORE_DEFAULT = 10


class RiskLevelSeverity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "recommendation"


def format_attr_name(s: str) -> str:
    return s.replace("_", " ").replace("/", " -> ").title()


def format_value(value: Any) -> str:
    if isinstance(value, Enum):
        return value.value
    return value


def format_display(data: Dict) -> Dict[str, str]:
    return {format_attr_name(k): format_value(v) for k, v in data.items()}


def get_knowledge_base_data_for_ooi_store(ooi_store) -> Dict[str, Dict]:
    knowledge_base = {}

    for ooi in ooi_store.values():
        # build knowledge base
        if ooi.get_information_id() not in knowledge_base:
            knowledge_base[ooi.get_information_id()] = get_knowledge_base_data_for_ooi(
                ooi
            )

    return knowledge_base


def get_knowledge_base_data_for_ooi(ooi: OOI) -> Dict:
    knowledge_base_data = {}

    # Knowledge base data
    information_id = ooi.get_information_id()
    if information_id != ooi.get_ooi_type():
        info, created = OOIInformation.objects.get_or_create(id=information_id)
        if info.description:
            knowledge_base_data.update(info.data)

        if isinstance(ooi, FindingType):
            knowledge_base_data.update(risk_level_calculate(ooi, info))

    try:
        info_on_type = OOIInformation.objects.get(id=ooi.get_ooi_type())
        knowledge_base_data["Information"] = info_on_type.description
    except OOIInformation.DoesNotExist:
        pass

    return knowledge_base_data


class RiskLevelScore(TypedDict):
    risk_level_source: Optional[Union[str, int, float]]
    risk_level_score: Union[int, float]
    risk_level_severity: str


def risk_level_calculate(ooi: FindingType, ooi_info: OOIInformation) -> RiskLevelScore:
    """
    Returns risk source value, calculated score and severity for finding type
    """

    if isinstance(ooi, CVEFindingType):
        return get_risk_level_score_for_cve(ooi_info.data)
    if isinstance(ooi, RetireJSFindingType):
        return get_risk_level_score_for_retirejs(ooi_info.data)
    if isinstance(ooi, SnykFindingType):
        return get_risk_level_score_for_snyk(ooi_info.data)

    return get_risk_level_score(ooi_info.data)


def get_risk_level_score_for_cve(data: Dict) -> RiskLevelScore:
    source = data.get("source")
    score = data.get("cvss", RISK_LEVEL_SCORE_DEFAULT) or RISK_LEVEL_SCORE_DEFAULT
    return {
        "risk_level_source": source,
        "risk_level_score": score,
        "risk_level_severity": risk_level_severity(score),
    }


def get_risk_level_score_for_retirejs(data: Dict) -> RiskLevelScore:
    source = RiskLevelSeverity[data["severity"].upper()].value
    score = risk_to_score(source or RISK_LEVEL_SCORE_DEFAULT)

    return {
        "risk_level_source": source,
        "risk_level_score": score,
        "risk_level_severity": risk_level_severity(score),
    }


def get_risk_level_score_for_snyk(data: Dict) -> RiskLevelScore:
    score = risk_to_score(float(data["risk"]) or RISK_LEVEL_SCORE_DEFAULT)

    return {
        "risk_level_source": score,
        "risk_level_score": score,
        "risk_level_severity": risk_level_severity(score),
    }


def get_risk_level_score(data: Dict) -> RiskLevelScore:
    source = data.get("risk")
    score = risk_to_score(data.get("risk", RISK_LEVEL_SCORE_DEFAULT))

    return {
        "risk_level_source": source,
        "risk_level_score": score,
        "risk_level_severity": risk_level_severity(score),
    }


def risk_to_score(risk: Union[str, int, float]) -> Union[int, float]:
    """
    Returns risk score 0 - 10
    Risk can be either string or number.
    text to score mapping guideline: CVSS v3 https://nvd.nist.gov/vuln-metrics/cvss
    """
    text_to_score_dict = {
        "critical": 10,
        "high": 8.9,
        "medium": 6.9,
        "low": 3.9,
        "very low": 0.0,
        "recommendation": 0.0,
        "middle": 6.9,
    }

    if isinstance(risk, (int, float)) and 0 <= risk <= 10:
        return risk

    if isinstance(risk, str) and risk.lower() in text_to_score_dict:
        return text_to_score_dict[risk.lower()]

    raise ValueError(f"Unknown risk level: {risk}")


def risk_level_severity(score: float) -> str:
    """
    Returns severity string, based on 0 - 10 score
    guideline: CVSS v3 https://nvd.nist.gov/vuln-metrics/cvss

    If no score or score not in 0-10 scale, return severity: critical
    """
    if score == 0:
        return RiskLevelSeverity.NONE.value
    elif score < 4:
        return RiskLevelSeverity.LOW.value
    elif score < 7:
        return RiskLevelSeverity.MEDIUM.value
    elif score < 9:
        return RiskLevelSeverity.HIGH.value
    else:
        return RiskLevelSeverity.CRITICAL.value


def process_value(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    return str(value) if value else None


def get_ooi_dict(ooi: OOI) -> Dict:
    ooi_dict = {
        "id": ooi.primary_key,
        "ooi_type": ooi.get_ooi_type(),
        "human_readable": ooi.human_readable,
    }

    ignore_properties = ["primary_key", "scan_profile"]

    # Props are everything but refs
    relations = get_relations(ooi.__class__)
    for attr_name, value in ooi:
        if attr_name not in relations and attr_name not in ignore_properties:
            ooi_dict[attr_name] = process_value(value)

    return ooi_dict


def get_tree_meta(tree_node: Dict, depth: int, location: str) -> Dict:
    tree_meta = {
        "depth": depth,
        "location": location,
        "child_count": "0",  # TO_DO ? child_count doesn't exist in template if not a string
        "has_findings": False,
        "has_jobs": False,
    }

    if "children" in tree_node:
        tree_meta["child_count"] = str(len(tree_node["children"]))
        tree_meta["child_ids"] = [child["id"] for child in tree_node["children"]]
        tree_meta["child_ooi_types"] = [
            child["ooi_type"] for child in tree_node["children"]
        ]

        for ooi_type in tree_meta["child_ooi_types"]:
            if ooi_type in ["Finding"]:
                tree_meta["has_findings"] = True
            if ooi_type == "Job":
                tree_meta["has_jobs"] = True

    return tree_meta


def create_object_tree_item_from_ref(
    reference_node: ReferenceNode,
    ooi_store: Dict[str, OOI],
    knowledge_base: Optional[Dict[str, Dict]] = None,
    depth=0,
    position=1,
    location="loc",
) -> Dict:
    depth = sum([depth, 1])
    location = location + "-" + str(position)

    ooi = ooi_store[str(reference_node.reference)]

    item = get_ooi_dict(ooi)

    if not knowledge_base:
        knowledge_base = get_knowledge_base_data_for_ooi_store(ooi_store)

    if knowledge_base[ooi.get_information_id()]:
        item.update(knowledge_base[ooi.get_information_id()])

    children = []
    child_position = 0
    for relation_name, child_items in reference_node.children.items():
        for child in child_items:
            if not child.reference.class_type.traversable():
                continue
            if child.reference == reference_node.reference:
                continue
            child_position = child_position + 1
            children.append(
                create_object_tree_item_from_ref(
                    child, ooi_store, knowledge_base, depth, child_position, location
                )
            )

    if children:
        item["children"] = children

    item["tree_meta"] = get_tree_meta(item, depth, location)

    return item


def get_ooi_types_from_tree(ooi, include_self=True):
    types = set()

    for child in ooi.get("children", []):
        for child_type in get_ooi_types_from_tree(child):
            types.add(child_type)

    if include_self:
        if ooi["ooi_type"] not in types:
            types.add(ooi["ooi_type"])

    return sorted(types)


def filter_ooi_tree(ooi_node: Dict, show_types=[], hide_types=[]) -> Dict:
    if not show_types and not hide_types:
        return ooi_node

    res = filter_ooi_tree_item(ooi_node, show_types, hide_types, True)

    return res[0]


def filter_ooi_tree_item(
    ooi_node, show_types, hide_types, self_excluded_from_filter=False
):
    def include_type(ooi_type):
        # hiding type takes precedence over showing type
        if hide_types and ooi_type in hide_types:
            return False

        if show_types:
            return ooi_type in show_types

        return True

    children = []

    if "children" in ooi_node:
        for child_ooi_node in ooi_node.get("children", []):
            children.extend(
                filter_ooi_tree_item(child_ooi_node, show_types, hide_types)
            )

        # no duplicates
        child_ids = set()
        ooi_node["children"] = []
        for child in children:
            if child.get("id") not in child_ids and child.get("id") != ooi_node["id"]:
                child_ids.add(child.get("id"))
                ooi_node["children"].append(child)

    if not self_excluded_from_filter and not include_type(ooi_node["ooi_type"]):
        return children

    return [ooi_node]


def get_finding_type_from_finding(finding: Finding) -> FindingType:
    return parse_obj_as(
        Union[
            KATFindingType,
            CVEFindingType,
            CWEFindingType,
            RetireJSFindingType,
            SnykFindingType,
        ],
        {
            "object_type": finding.finding_type.class_,
            "id": finding.finding_type.natural_key,
        },
    )


_EXCLUDED = [Finding] + FindingType.__subclasses__()
OOI_TYPES_WITHOUT_FINDINGS = [
    name for name, cls_ in OOI_TYPES.items() if cls_ not in _EXCLUDED
]


def get_or_create_ooi(
    api_connector: OctopoesAPIConnector, ooi: OOI, observed_at: datetime = None
) -> Tuple[OOI, Union[bool, datetime]]:
    _now = datetime.now(timezone.utc)
    if observed_at is None:
        observed_at = _now

    try:
        return api_connector.get(ooi.reference, observed_at), False
    except ObjectNotFoundException:
        if observed_at < _now:
            # don't create an OOI when expected valid_time is in the past
            raise ValueError(f"OOI not found and unable to create at {observed_at}")
        create_ooi(api_connector, ooi, observed_at)
        return ooi, datetime.now(timezone.utc)


def create_ooi(
    api_connector: OctopoesAPIConnector, ooi: OOI, observed_at: datetime = None
) -> None:
    if observed_at is None:
        observed_at = datetime.now(timezone.utc)

    api_connector.save_declaration(Declaration(ooi=ooi, valid_time=observed_at))
