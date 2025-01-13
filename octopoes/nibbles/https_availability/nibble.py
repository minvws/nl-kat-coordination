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

    base_query = [
        """
            [?website :Website/ip_service ?ip_service]
            [?ipservice :IPService/ip_port ?ipport80]
            [?ipport80 :IPPort/port 80]
            [?ipport80 :IPPort/address ?ipaddress]
            (or
               (and [?ipport443 :IPPort/address ?ipaddress][?ipport443 :IPPort/port 443])
               [(identity nil) ?ipport443]
            )
        """
    ]

    sgn = "".join(str(int(isinstance(target, Reference))) for target in targets)
    if sgn == "1000":
        return pull([f'[?ipaddress :IPAddress/primary_key "{str(targets[0])}"]'] + base_query)
    elif sgn == "0100":
        if int(str(targets[1]).split("|")[-1]) == 80:
            return pull([f'[?ipport80 :IPPort/primary_key "{str(targets[1])}"]'] + base_query)
        else:
            return pull(base_query)
    elif sgn == "0010":
        return pull([f'[?website :Website/primary_key "{str(targets[2])}"]'] + base_query)
    else:
        return pull(base_query)


NIBBLE = NibbleDefinition(
    id="https_availability",
    signature=[
        NibbleParameter(
            object_type=IPAddress, parser="[*][?object_type == 'IPAddressV6' || object_type == 'IPAddressV4'][]"
        ),
        NibbleParameter(object_type=IPPort, parser="[*][?object_type == 'IPPort'][]"),
        NibbleParameter(object_type=Website, parser="[*][?object_type == 'Website'][]"),
        NibbleParameter(object_type=int, parser="[*][-1][]"),
    ],
    query=query,
)
