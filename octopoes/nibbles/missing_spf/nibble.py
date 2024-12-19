from nibbles.definitions import NibbleDefinition, NibbleParameter
from octopoes.models import Reference
from octopoes.models.ooi.dns.records import NXDOMAIN
from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.ooi.email_security import DNSSPFRecord


def spf_query(targets: list[Reference | None]) -> str:
    sgn = "".join(str(int(isinstance(target, Reference))) for target in targets)
    if sgn == "100":
        return f"""
                    {{
                        :query {{
                            :find [(pull ?hostname [*]) (pull ?spf [*]) (pull ?nx [*])] :where [

                                [?hostname :object_type "Hostname"]
                                [?hostname :Hostname/primary_key "{str(targets[0])}"]

                                (or
                                    (and
                                        [?spf :object_type "DNSSPFRecord"]
                                        [?spf :DNSSPFRecord/dns_txt_record ?txt]
                                        [?txt :DNSTXTRecord/hostname ?hostname]
                                    )
                                    (and
                                        [(identity nil) ?spf]
                                        [(identity nil) ?txt]
                                    )
                                )

                                (or
                                    (and
                                        [?nx :object_type "NXDOMAIN"]
                                        [?nx :NXDOMAIN/hostname ?hostname]
                                    )
                                    (and
                                        [(identity nil) ?nx]
                                    )
                                )

                            ]
                        }}
                    }}
                """
    elif sgn == "010":
        return f"""
                    {{
                        :query {{
                            :find [(pull ?hostname [*]) (pull ?spf [*]) (pull ?nx [*])] :where [

                                [?spf :object_type "DNSSPFRecord"]
                                [?spf :DNSSPFRecord/primary_key "{str(targets[1])}"]
                                [?spf :DNSSPFRecord/dns_txt_record ?txt]
                                [?txt :DNSTXTRecord/hostname ?hostname]

                                (or
                                    (and
                                        [?nx :object_type "NXDOMAIN"]
                                        [?nx :NXDOMAIN/hostname ?hostname]
                                    )
                                    (and
                                        [(identity nil) ?nx]
                                    )
                                )

                            ]
                        }}
                    }}
                """
    elif sgn == "001":
        return f"""
                    {{
                        :query {{
                            :find [(pull ?hostname [*]) (pull ?spf [*]) (pull ?nx [*])] :where [

                                [?nx :object_type "NXDOMAIN"]
                                [?nx :NXDOMAIN/primary_key "{str(targets[2])}"]
                                [?nx :NXDOMAIN/hostname ?hostname]

                                (or
                                    (and
                                        [?spf :object_type "DNSSPFRecord"]
                                        [?spf :DNSSPFRecord/dns_txt_record ?txt]
                                        [?txt :DNSTXTRecord/hostname ?hostname]
                                    )
                                    (and
                                        [(identity nil) ?spf]
                                        [(identity nil) ?txt]
                                    )
                                )
                            ]
                        }}
                    }}
                """
    elif sgn == "111":
        return f"""
                           {{
                               :query {{
                                   :find [(pull ?hostname [*]) (pull ?spf [*]) (pull ?nx [*])] :where [
                                        [?hostname :object_type "Hostname"]
                                        [?hostname :Hostname/primary_key "{str(targets[0])}"]
                                        [?spf :object_type "DNSSPFRecord"]
                                        [?spf :DNSSPFRecord/primary_key "{str(targets[1])}"]
                                        [?nx :object_type "NXDOMAIN"]
                                        [?nx :NXDOMAIN/primary_key "{str(targets[2])}"]
                                      ]
                                 }}
                            }}
                        """
    else:
        return """
                    {
                        :query {
                            :find [(pull ?hostname [*]) (pull ?spf [*]) (pull ?nx [*])] :where [

                                [?hostname :object_type "Hostname"]

                                (or
                                    (and
                                        [?spf :object_type "DNSSPFRecord"]
                                        [?spf :DNSSPFRecord/dns_txt_record ?txt]
                                        [?txt :DNSTXTRecord/hostname ?hostname]
                                    )
                                    (and
                                        [(identity nil) ?spf]
                                        [(identity nil) ?txt]
                                    )
                                )

                                (or
                                    (and
                                        [?nx :object_type "NXDOMAIN"]
                                        [?nx :NXDOMAIN/hostname ?hostname]
                                    )
                                    (and
                                        [(identity nil) ?nx]
                                    )
                                )

                            ]
                        }
                    }
                """


NIBBLE = NibbleDefinition(
    id="missing_spf",
    signature=[
        NibbleParameter(object_type=Hostname, parser="[*][?object_type == 'Hostname'][]"),
        NibbleParameter(object_type=DNSSPFRecord, parser="[*][?object_type == 'DNSSPFRecord'][]", optional=True),
        NibbleParameter(object_type=NXDOMAIN, parser="[*][?object_type == 'NXDOMAIN'][]", optional=True),
    ],
    query=spf_query,
)
