from nibbles.definitions import NibbleDefinition, NibbleParameter
from octopoes.models import Reference
from octopoes.models.ooi.findings import FindingType


def query(targets: list[Reference | None]) -> str:
    ooi_type = targets[0].split("|")[0] if targets[0] else None
    if ooi_type:
        return f"""
                {{
                    :query {{
                        :find[(pull ?findingtype[*])]
                        :where
                        [
                            [?findingtype :{ooi_type}/primary_key "{targets[0]}"]
                        ]
                    }}
                }}
    """
    else:
        return """
                {
                    :query {
                        :find[(pull ?findingtype[*])]
                        :where
                        [
                            [?findingtype :object_type ?object_type]
                            [(clojure.string/includes? ?object_type "FindingType")]
                        ]
                    }
                }
            """


NIBBLE = NibbleDefinition(
    id="default-findingtype-risk",
    signature=[
        NibbleParameter(object_type=FindingType, parser="[*][?contains(object_type, 'FindingType')][]"),
        NibbleParameter(object_type=int, parser="[*][?object_type == 'KATFindingType'][] | [length(@)]"),
    ],
    query=query,
)
