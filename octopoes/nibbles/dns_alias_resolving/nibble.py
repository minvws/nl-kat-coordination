from nibbles.definitions import NibbleDefinition, NibbleParameter
from octopoes.models import Reference
from octopoes.models.ooi.dns.records import DNSCNAMERecord
from octopoes.models.ooi.dns.zone import Hostname, ResolvedHostname


def query(params: list[Reference | None]) -> str:
    hostname, dns_record, resolved_hostname = params

    def pull(query: str) -> str:
        return f"""
                {{
                    :query {{
                        :find [(pull ?hostname [*]) (pull ?dns_record [*]) (pull ?resolved_hostname [*])] :where [
                            {query}
                        ]
                    }}
                }}
        """

    dns_record_from_hostname = """
        [?dns_record :object_type "DNSCNAMERecord"]
        [?dns_record :DNSCNAMERecord/target_hostname ?hostname]
    """

    resolved_hostname_from_hostname = """
        [?resolved_hostname :object_type "ResolvedHostname"]
        [?resolved_hostname :ResolvedHostname/hostname ?hostname]
    """

    sgn = "".join(str(int(isinstance(target, Reference))) for target in params)
    if sgn == "100":
        return pull(
            f"""
                [?hostname :object_type "Hostname"]
                [?hostname :Hostname/primary_key "{hostname}"]

                {dns_record_from_hostname}

                {resolved_hostname_from_hostname}
            """
        )
    elif sgn == "010":
        return pull(
            f"""
                [?dns_record :object_type "DNSCNAMERecord"]
                [?dns_record :DNSCNAMERecord/primary_key "{dns_record}"]
                [?dns_record :DNSCNAMERecord/target_hostname ?hostname]

                {resolved_hostname_from_hostname}
            """
        )
    elif sgn == "001":
        return pull(
            f"""
                [?resolved_hostname :object_type "ResolvedHostname"]
                [?resolved_hostname :ResolvedHostname/primary_key "{resolved_hostname}"]
                [?resolved_hostname :ResolvedHostname/hostname ?hostname]

                {dns_record_from_hostname}
            """
        )
    elif sgn == "111":
        return pull(
            f"""
                [?hostname :object_type "Hostname"]
                [?hostname :Hostname/primary_key "{hostname}"]
                [?dns_record :object_type "DNSCNAMERecord"]
                [?dns_record :DNSCNAMERecord/primary_key "{dns_record}"]
                [?resolved_hostname :object_type "ResolvedHostname"]
                [?resolved_hostname :ResolvedHostname/primary_key "{resolved_hostname}"]
            """
        )
    else:
        # ? Is there a reason for this to be an option?
        return pull(
            """
                [?hostname :object_type "Hostname"]
                [?dns_record :object_type "DNSCNAMERecord"]
                [?resolved_hostname :object_type "ResolvedHostname"]
            """
        )


NIBBLE = NibbleDefinition(
    id="dns-alias-resolving",
    signature=[
        NibbleParameter(object_type=Hostname, parser="[*][?object_type == 'Hostname'][]"),
        NibbleParameter(object_type=DNSCNAMERecord, parser="[*][?object_type == 'DNSCNAMERecord'][]"),
        NibbleParameter(object_type=ResolvedHostname, parser="[*][?object_type == 'ResolvedHostname'][]"),
    ],
    query=query,
)
