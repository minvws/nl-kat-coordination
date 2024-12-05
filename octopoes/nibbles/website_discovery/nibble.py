from nibbles.definitions import NibbleDefinition, NibbleParameter
from octopoes.models.ooi.dns.zone import ResolvedHostname
from octopoes.models.ooi.service import IPService

NIBBLE = NibbleDefinition(
    name="website_discovery",
    signature=[
        NibbleParameter(object_type=ResolvedHostname, parser="[*][?object_type == 'ResolvedHostname'][]"),
        NibbleParameter(object_type=IPService, parser="[*][?object_type == 'IPService'][]"),
    ],
    query="""{
            :query {
                :find [(pull ?var [*])]
                :where [
                    (or
                        (and
                            [?var :object_type "ResolvedHostname"]
                            [?var :ResolvedHostname/address ?ip_address]
                            [?ip_service :object_type "IPService"]
                            [?ip_service :IPService/ip_port ?ip_port]
                            [?ip_service :IPService/service ?service]
                            (or [?service :Service/name "http"][?service :Service/name "https"])
                            [?ip_port :IPPort/address ?ip_address]
                            [?var :ResolvedHostname/primary_key $1]
                            [?resolved_hostname :object_type]
                        )
                        (and
                            [?var :object_type "IPService"]
                            [?var :IPService/ip_port ?ip_port]
                            [?var :IPService/service ?service]
                            (or [?service :Service/name "http"][?service :Service/name "https"])
                            [?ip_port :IPPort/address ?ip_address]
                            [?resolved_hostname :object_type "ResolvedHostname"]
                            [?resolved_hostname :ResolvedHostname/address ?ip_address]
                            [?var :IPService/primary_key $2]
                            [?ip_service :object_type]
                        )
                    )
                ]
            }
            }
        """,
)
