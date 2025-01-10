from nibbles.definitions import NibbleDefinition, NibbleParameter
from octopoes.models import Reference
from octopoes.models.ooi.dns.records import DNSCNAMERecord
from octopoes.models.ooi.dns.zone import Hostname, ResolvedHostname


def query(params: list[Reference]) -> str:
    hostname, dns_record, resolved_hostname = list(f'"{target}"' for target in params)
    return f"""
        {{
        :query {{
                    :find [(pull ?var [*])]
                    :where [
                        (or
                            (and
                                [?var :object_type "Hostname"]
                                [?var :Hostname/primary_key {hostname}]
                                [?var :Hostname/name ?hostname]
                            )

                            (and
                                [?var :object_type "DNSCNAMERecord"]
                                [?var :DNSCNAMERecord/primary_key {dns_record}]
                                [?var :DNSCNAMERecord/target_hostname ?hostname]
                            )

                            (and
                                [?var :object_type "ResolvedHostname"]
                                [?var :ResolvedHostname/primary_key {resolved_hostname}]
                                [?var :ResolvedHostname/hostname ?hostname]
                            )
                        )
                    ]
            }}
        }}
    """


NIBBLE = NibbleDefinition(
    id="dns-alias-resolving",
    signature=[
        NibbleParameter(object_type=Hostname, parser="[*][?object_type == 'Hostname'][]"),
        NibbleParameter(object_type=DNSCNAMERecord, parser="[*][?object_type == 'DNSCNAMERecord'][]"),
        NibbleParameter(object_type=ResolvedHostname, parser="[*][?object_type == 'ResolvedHostname'][]"),
    ],
    query=query,
)
