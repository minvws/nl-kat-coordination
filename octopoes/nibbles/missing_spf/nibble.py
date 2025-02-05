from nibbles.definitions import NibbleDefinition, NibbleParameter
from octopoes.models import Reference
from octopoes.models.ooi.dns.records import NXDOMAIN
from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.ooi.email_security import DNSSPFRecord


def spf_query(targets: list[Reference | None]) -> str:
    def pull(statements: list[str]) -> str:
        return f"""
            {{
                :query {{
                    :find [(pull ?var [*])] :where [
                        {" ".join(statements)}

                        (or-join [?var ?hostname]
                            [?var :Hostname/primary_key ?hostname]
                            (and
                                [?var :DNSSPFRecord/dns_txt_record ?txt]
                                [?txt :DNSTXTRecord/hostname ?hostname]
                            )
                            [?var :NXDOMAIN/hostname ?hostname]
                        )
                    ]
                }}
            }}
        """

    sgn = "".join(str(int(isinstance(target, Reference))) for target in targets)
    if sgn == "100":
        return pull(
            [
                f"""
                    [?hostname :Hostname/primary_key "{str(targets[0])}"]
                """
            ]
        )
    elif sgn == "010":
        return pull(
            [
                f"""
                    [?spf :DNSSPFRecord/primary_key "{str(targets[1])}"]
                    [?spf :DNSSPFRecord/dns_txt_record ?txt]
                    [?txt :DNSTXTRecord/hostname ?hostname]
                """
            ]
        )
    elif sgn == "001":
        return pull(
            [
                f"""
                    [?nx :NXDOMAIN/primary_key "{str(targets[2])}"]
                    [?nx :NXDOMAIN/hostname ?hostname]
                """
            ]
        )
    elif sgn == "111":
        return f"""
            {{
                :query {{
                    :find [(pull ?var [*])] :where [
                        (or-join [?var]
                            [?var :Hostname/primary_key "{str(targets[0])}"]
                            [?var :DNSSPFRecord/primary_key "{str(targets[1])}"]
                            [?var :NXDOMAIN/primary_key "{str(targets[2])}"]
                        )
                    ]
                 }}
            }}
        """
    else:
        return pull(
            [
                """
                    [?hostname :Hostname/object_type "Hostname"]
                """
            ]
        )


NIBBLE = NibbleDefinition(
    id="missing_spf",
    signature=[
        NibbleParameter(object_type=Hostname, parser="[*][?object_type == 'Hostname'][]"),
        NibbleParameter(object_type=DNSSPFRecord, parser="[*][?object_type == 'DNSSPFRecord'][]", optional=True),
        NibbleParameter(object_type=NXDOMAIN, parser="[*][?object_type == 'NXDOMAIN'][]", optional=True),
    ],
    query=spf_query,
)
