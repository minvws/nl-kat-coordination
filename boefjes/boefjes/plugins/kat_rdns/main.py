import dns
from dns.resolver import Answer
from dns.edns import EDEOption

from boefjes.config import settings
from boefjes.job_models import BoefjeMeta


def run(boefje_meta: BoefjeMeta) -> list[tuple[set, bytes | str]]:
    """return results to normalizer."""
    ip = boefje_meta.arguments["input"]["address"]

    resolver = dns.resolver.Resolver()
    # https://dnspython.readthedocs.io/en/stable/_modules/dns/edns.html
    # enable EDE to get the ServFail return values if the server supports it # codespell-ignore
    resolver.use_edns(options=[EDEOption(15)])
    resolver.nameservers = [str(settings.remote_ns)]
    reverse_ip = dns.reversename.from_address(ip)
    try:
        answer: Answer = resolver.resolve(reverse_ip, "PTR")
        result = f"RESOLVER: {answer.nameserver}\n{answer.response}"
        return [(set(), result)]
    except dns.resolver.NXDOMAIN:
        return [(set(), "NXDOMAIN")]
    except dns.resolver.NoNameservers as error:
        # no servers responded happily, we'll check the response from the first
        # https://dnspython.readthedocs.io/en/latest/_modules/dns/rcode.html
        # https://www.rfc-editor.org/rfc/rfc8914#name-extended-dns-error-code-6-d
        firsterror = error.kwargs["errors"][0]
        if firsterror[3] == "SERVFAIL":
            for edeerror in firsterror[4].options:
                if int(edeerror.code) == 22:
                    # Auth nameserver for ip could not be reached, error codes defined in RFC 8914
                    return [(set(), "NoAuthServersReachable:" + edeerror.text)]  
                    # returned when the resolver indicates a Lame delegation.
        return [(set(), "SERVFAIL")]
    except (dns.resolver.Timeout, dns.resolver.NoAnswer):
        return [(set(), "NoAnswer")]
