from nibbles.definitions import NibbleDefinition, NibbleParameter
from octopoes.models import Reference
from octopoes.models.ooi.dns.zone import Hostname, Network
from octopoes.models.ooi.findings import Finding
from octopoes.models.ooi.web import Website

finding_types = [
    "KAT-WEBSERVER-NO-IPV6",
    "KAT-NAMESERVER-NO-TWO-IPV6",
    "KAT-NO-DNSSEC",
    "KAT-INVALID-DNSSEC",
    "KAT-NO-HSTS",
    "KAT-NO-CSP",
    "KAT-NO-X-FRAME-OPTIONS",
    "KAT-NO-X-CONTENT-TYPE-OPTIONS",
    "KAT-CSP-VULNERABILITIES",
    "KAT-HSTS-VULNERABILITIES",
    "KAT-NO-CERTIFICATE",
    "KAT-HTTPS-NOT-AVAILABLE",
    "KAT-SSL-CERT-HOSTNAME-MISMATCH",
    "KAT-HTTPS-REDIRECT",
]


def or_finding_types() -> str:
    clauses = "".join([f'[?finding :Finding/finding_type "{ft}"]' for ft in finding_types])
    return f"(or {clauses})"


def query(targets: list[Reference | None]) -> str:
    def pull(statements: list[str]) -> str:
        return f"""
                {{
                    :query {{
                        :find [(pull ?hostname [*]) (pull ?finding [*])]
                        :where [
                            {" ".join(statements)}
                        ]
                    }}
                }}
        """

    base_query = [
        """
            [?website :Website/hostname ?hostname]
            [?finding :Finding/ooi ?ooi]
            (or
                (or
                    (and
                        [?ooi :Hostname/primary_key ?hostname]
                    )
                    (and
                        [(identity nil) ?ooi]
                    )
                )
                (or
                    (and
                        [?ooi :HTTPResource/website ?website]
                        [?website :Website/hostname ?hostname]
                    )
                    (and
                        [(identity nil) ?ooi]
                        [(identity nil) ?website]
                    )
                )
                (or
                    (and
                        [?ooi :HTTPHeader/website ?resource]
                        [?resource :HTTPResource/website ?website]
                        [?website :Website/hostname ?hostname]
                    )
                    (and
                        [(identity nil) ?ooi]
                        [(identity nil) ?resource]
                        [(identity nil) ?website]
                    )
                )
                (or
                    (and
                        [?ooi :Website/hostname ?hostname]
                    )
                    (and
                        [(identity nil) ?ooi]
                    )
                )
                (or
                    (and
                        [?ooi :HostnameHTTPURL/hostname ?hostname]
                    )
                    (and
                        [(identity nil) ?ooi]
                    )
                )
            )
        """
    ]

    sgn = "".join(str(int(isinstance(target, Reference))) for target in targets)
    ref_query = ["[?hostname :Hostname/primary_key]"]
    if sgn == "100":
        ref_query = [f'[?hostname :Hostname/primary_key "{str(targets[0])}"]']
    elif sgn == "010":
        ref_query = [f'[?hostname :Hostname/primary_key "{str(targets[1]).split("|")[-1]}"]']
    elif sgn == "001":
        tokens = str(targets[2]).split("|")[1:-1]
        target_reference = Reference.from_str("|".join(tokens))
        if tokens[0] == "Hostname":
            hostname = target_reference.tokenized
        elif tokens[0] == "HTTPResource":
            hostname = target_reference.tokenized.website.hostname
        elif tokens[0] == "HTTPHeader":
            hostname = target_reference.tokenized.resource.website.hostname
        elif tokens[0] in {"Website", "HostnameHTTPURL"}:
            hostname = target_reference.tokenized.hostname
        else:
            raise ValueError()
        hostname_pk = Hostname(name=hostname.name, network=Network(name=hostname.network.name).reference).reference
        ref_query = [f'[?hostname :Hostname/primary_key "{str(hostname_pk)}"]']
    return pull(ref_query + base_query)


NIBBLE = NibbleDefinition(
    id="internet_nl",
    signature=[
        NibbleParameter(object_type=Hostname, parser="[*][?object_type == 'IPPort'][]"),
        NibbleParameter(object_type=list[Website], parser="[[*][?object_type == 'Website'][]]", additional={Website}),
        NibbleParameter(object_type=list[Finding], parser="[[*][?object_type == 'Findings'][]]", additional={Finding}),
    ],
    query=query,
)
