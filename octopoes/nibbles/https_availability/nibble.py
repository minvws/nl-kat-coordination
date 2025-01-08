from nibbles.definitions import NibbleDefinition, NibbleParameter
from octopoes.models import Reference
from octopoes.models.ooi.network import IPAddress, IPPort
from octopoes.models.ooi.web import Website


def query(targets: list[Reference | None]) -> str:
    def pull(statements: list[str]) -> str:
        return f"""
                {{
                    :query {{
                        :find [(pull ?ipaddress [*]) (pull ?ipport80 [*]) (pull ?ipport443 [*]) (pull ?website [*])]
                        :where [
                            {" ".join(statements)}
                        ]
                    }}
                }}
        """

    sgn = "".join(str(int(isinstance(target, Reference))) for target in targets)
    if sgn == "1000":
        return pull(
            [
                f"""
            [?ipaddress :object_type "IPAddressV4"]
            [?ipaddress :IPAddressV4/primary_key "{str(targets[0])}"]
            [?ipport80 :IPPort/address ?ipaddress]
            [?ipport80 :IPPort/port 80]
            (or
               (and [?ipport443 :IPPort/address ?ipaddress][?ipport443 :IPPort/port 443])
               (and [(identity 0) ?ipport443])
            )
            [?ip_service :IPService/ip_port ?ipport80]
            [?website :Website/ip_service ?ip_service]
            """
            ]
        )
    return "potato"


NIBBLE = NibbleDefinition(
    id="https-availability",
    signature=[
        NibbleParameter(object_type=IPAddress, parser="[*][?object_type == 'IPAddressV4'][]"),
        NibbleParameter(object_type=IPPort, parser='[*][?"IPPort/port" == "80"][]'),
        NibbleParameter(object_type=Website, parser="[*][?object_type == 'Website'][]"),
        NibbleParameter(object_type=int, parser='[length([*][?"IPPort/port" == "443"])]'),
    ],
    query=query,
)
