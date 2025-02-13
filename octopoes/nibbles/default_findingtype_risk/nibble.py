from nibbles.definitions import NibbleDefinition, NibbleParameter
from octopoes.models import Reference
from octopoes.models.ooi.findings import FindingType


def query(targets: list[Reference | None]) -> str:
    return f"""
                {{
                    :query {{
                        :find[(pull ?findingtype[*])]
                        :where
                        [
                            [?findingtype :KATFindingType/primary_key "{targets[0]}"]
                        ]
                    }}
                }}
    """


NIBBLE = NibbleDefinition(
    id="default-findingtype-risk",
    signature=[
        NibbleParameter(object_type=FindingType, parser="[*][?object_type == 'FindingType'][]"),
        NibbleParameter(object_type=int, parser="[*][?object_type == 'KATFindingType'][] | [length(@)]"),
    ],
    query=query,
)
