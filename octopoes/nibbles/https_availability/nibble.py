from nibbles.definitions import NibbleDefinition, NibbleParameter
from octopoes.models import Reference
from octopoes.models.ooi.network import IPAddress, IPPort
from octopoes.models.ooi.web import Website


def query(targets: list[Reference | None]) -> str:
    def pull(statements: list[str]) -> str:
        return f"""
                {{
                    :query {{
                        :find [(pull ?ipaddress [*]) (pull ?ipport80 [*]) (pull ?website [*]) (count ?ipport443)]
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
                (or
                    (and [?ipaddress :object_type "IPAddressV4"]
                         [?ipaddress :IPAddressV4/primary_key "{str(targets[0])}"]
                    )
                    (and [?ipaddress :object_type "IPAddressV6"]
                         [?ipaddress :IPAddressV6/primary_key "{str(targets[0])}"]
                    )
                )
                [?ipport80 :IPPort/address ?ipaddress]
                [?ipport80 :IPPort/port 80]
                [?ip_service :IPService/ip_port ?ipport80]
                [?website :Website/ip_service ?ip_service]
                (or
                   (and [?ipport443 :IPPort/address ?ipaddress][?ipport443 :IPPort/port 443])
                   [(identity nil) ?ipport443]
                )
            """
            ]
        )
    elif sgn == "0100" or sgn == "0010" or sgn == "1110":
        return "TODO"
    else:
        return "TODO"


NIBBLE = NibbleDefinition(
    id="https_availability",
    signature=[
        NibbleParameter(object_type=IPAddress, parser="[*][?object_type == 'IPAddressV4'][]"),
        NibbleParameter(object_type=IPPort, parser="[*][?object_type == 'IPPort'][]"),
        NibbleParameter(object_type=Website, parser="[*][?object_type == 'Website'][]"),
        NibbleParameter(object_type=int, parser="[*][-1][]"),
    ],
    query=query,
)
