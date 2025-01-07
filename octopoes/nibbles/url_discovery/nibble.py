from nibbles.definitions import NibbleDefinition, NibbleParameter
from octopoes.models import Reference
from octopoes.models.ooi.dns.zone import ResolvedHostname
from octopoes.models.ooi.network import IPPort


def url_query(targets: list[Reference | None]) -> str:
    links = list(f'"{target}"' if isinstance(target, Reference) else "" for target in targets)
    return f"""{{
            :query {{
                :find [(pull ?var [*])]
                :where [
                    (or
                        (and
                            [?var :object_type "ResolvedHostname"]
                            [?var :ResolvedHostname/address ?ip_address]
                            [?ip_port :IPPort/address ?ip_address]
                            (or [?ip_port :IPPort/port 443][?ip_port :IPPort/port 80])
                            [?var :ResolvedHostname/primary_key {links[1]}]
                            [?resolved_hostname :object_type]
                        )
                        (and
                            [?var :object_type "IPPort"]
                            [?ip_port :IPPort/address ?ip_address]
                            (or [?ip_port :IPPort/port 443][?ip_port :IPPort/port 80])
                            [?resolved_hostname :object_type "ResolvedHostname"]
                            [?resolved_hostname :ResolvedHostname/address ?ip_address]
                            [?var :IPPort/primary_key {links[0]}]
                            [?ip_port :object_type]
                        )
                    )
                ]
            }}
            }}
        """


NIBBLE = NibbleDefinition(
    id="url-discovery",
    signature=[
        NibbleParameter(object_type=IPPort, parser="[*][?object_type == 'IPPort'][]"),
        NibbleParameter(
            object_type=ResolvedHostname, parser="[*][?object_type == 'ResolvedHostname'][]", optional=True
        ),
    ],
    query=url_query,
)
