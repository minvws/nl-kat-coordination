from nibbles.definitions import NibbleDefinition, NibbleParameter
from octopoes.models import Reference
from octopoes.models.ooi.dns.records import NXDOMAIN
from octopoes.models.ooi.web import HTTPHeaderHostname


def query(targets: list[Reference | None]) -> str:
    def pull(statements: list[str]) -> str:
        return f"""
            {{
                :query {{
                    :find [(pull ?var [*])] :where [
                        {" ".join(statements)}
                        (or-join [?var ?hostname]
                            [?var :NXDOMAIN/hostname ?hostname]
                            [?var :HTTPHeaderHostname/hostname ?hostname]
                        )
                    ]
                }}
            }}
        """

    sgn = "".join(str(int(isinstance(target, Reference))) for target in targets)

    if sgn == "1":
        return pull(
            [
                f"""
                    [?var :HTTPHeaderHostname/primary_key "{str(targets[0])}"]
                """
            ]
        )

    else:
        return pull([""])


NIBBLE = NibbleDefinition(
    id="nxdomain_header_flag",
    signature=[
        NibbleParameter(
            object_type=HTTPHeaderHostname, parser="[*][?object_type == 'HTTPHeaderHostname'][]", additional={NXDOMAIN}
        )
    ],
    query=query,
)
