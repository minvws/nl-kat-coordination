from nibbles.definitions import NibbleDefinition, NibbleParameter
from octopoes.models import Reference
from octopoes.models.ooi.dns.records import DNSCNAMERecord
from octopoes.models.ooi.dns.zone import ResolvedHostname


def query(params: list[Reference | None]) -> str:
    dns_record, resolved_hostname = params

    def pull(query: str) -> str:
        return f"""
                {{
                    :query {{
                        :find [(pull ?dns_record [*]) (pull ?resolved_hostname [*])] :where [
                            {query}
                        ]
                    }}
                }}
        """

    sgn = "".join(str(int(isinstance(target, str))) for target in params)

    if sgn == "10":
        return pull(
            f"""
                [?dns_record :object_type "DNSCNAMERecord"]
                [?dns_record :DNSCNAMERecord/primary_key "{dns_record}"]
                [?dns_record :DNSCNAMERecord/target_hostname ?hostname]

                [?resolved_hostname :object_type "ResolvedHostname"]
                [?resolved_hostname :ResolvedHostname/hostname ?hostname]
            """
        )
    elif sgn == "01":
        return pull(
            f"""
                [?resolved_hostname :object_type "ResolvedHostname"]
                [?resolved_hostname :ResolvedHostname/primary_key "{resolved_hostname}"]
                [?resolved_hostname :ResolvedHostname/hostname ?hostname]

                [?dns_record :object_type "DNSCNAMERecord"]
                [?dns_record :DNSCNAMERecord/target_hostname ?hostname]
            """
        )
    elif sgn == "11":
        return pull(
            f"""
                [?dns_record :object_type "DNSCNAMERecord"]
                [?dns_record :DNSCNAMERecord/primary_key "{dns_record}"]
                [?resolved_hostname :object_type "ResolvedHostname"]
                [?resolved_hostname :ResolvedHostname/primary_key "{resolved_hostname}"]
            """
        )
    else:
        return pull(
            """
                [?dns_record :object_type "DNSCNAMERecord"]
                [?dns_record :DNSCNAMERecord/target_hostname ?hostname]

                [?resolved_hostname :object_type "ResolvedHostname"]
                [?resolved_hostname :ResolvedHostname/hostname ?hostname]
            """
        )


NIBBLE = NibbleDefinition(
    id="dns-alias-resolving",
    signature=[
        NibbleParameter(object_type=DNSCNAMERecord, parser="[*][?object_type == 'DNSCNAMERecord'][]"),
        NibbleParameter(object_type=ResolvedHostname, parser="[*][?object_type == 'ResolvedHostname'][]"),
    ],
    query=query,
)
