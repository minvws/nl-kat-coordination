import re
import sys
from ipaddress import IPv4Address, IPv6Address
from os import getenv

import dns
from dns.edns import EDEOption
from dns.message import from_text
from dns.name import Name
from dns.rdtypes.ANY.CAA import CAA
from dns.rdtypes.ANY.CNAME import CNAME
from dns.rdtypes.ANY.MX import MX
from dns.rdtypes.ANY.NS import NS
from dns.rdtypes.ANY.SOA import SOA
from dns.rdtypes.ANY.TXT import TXT
from dns.rdtypes.IN.A import A
from dns.rdtypes.IN.AAAA import AAAA
from dns.resolver import Answer

DEFAULT_RECORD_TYPES = {"A", "AAAA", "CAA", "CERT", "RP", "SRV", "TXT", "MX", "NS", "CNAME", "DNAME", "SOA"}


class TimeoutException(Exception):
    pass


class ZoneNotFoundException(Exception):
    pass


def get_record_types() -> set[str]:
    requested_record_types = getenv("RECORD_TYPES", "")
    if not requested_record_types:
        return DEFAULT_RECORD_TYPES
    parsed_requested_record_types = map(
        lambda x: re.sub(r"[^A-Za-z]", "", x), requested_record_types.upper().split(",")
    )
    return set(parsed_requested_record_types).intersection(DEFAULT_RECORD_TYPES)


def run(hostname: str) :
    requested_dns_name = dns.name.from_text(hostname)
    resolver = dns.resolver.Resolver()

    # https://dnspython.readthedocs.io/en/stable/_modules/dns/edns.html
    # enable EDE to get the DNSSEC Bogus return values if the server supports it # codespell-ignore
    resolver.use_edns(options=[EDEOption(15)])
    nameserver = getenv("REMOTE_NS", "1.1.1.1")
    resolver.nameservers = [nameserver]

    record_types = get_record_types()
    answers = [get_parent_zone_soa(resolver, requested_dns_name)] if "SOA" in record_types else []

    for type_ in record_types:
        try:
            answer: Answer = resolver.resolve(hostname, type_)
            answers.append(answer)
        except (dns.resolver.NoAnswer, dns.resolver.Timeout):
            pass
        except dns.resolver.NXDOMAIN:
            return

    dmarc_results = get_email_security_records(resolver, hostname, "_dmarc")
    dkim_results = get_email_security_records(resolver, hostname, "_domainkey")

    if not answers and dmarc_results == "Timeout" and dkim_results == "Timeout":
        raise TimeoutException("No answers from DNS-Server due to timeouts.")

    internet = dict(name="internet")

    zone = None
    hostname_store = {}
    record_store = []

    def register_hostname(name: str) -> dict:
        hostname = dict(network=internet["name"], name=name.rstrip("."))
        hostname_store[hostname["name"]] = hostname
        return hostname

    def register_record(record: dict) -> dict:
        record_store.append(record)
        return record

    # register argument hostname
    input_hostname = register_hostname(hostname)

    # keep track of discovered zones
    zone_links = {}
    results = []

    for answer in answers:
        for rrset in answer.response.answer:
            for rr in rrset:
                record_hostname = register_hostname(str(rrset.name))
                default_args = {"hostname": record_hostname["name"], "value": str(rr), "ttl": rrset.ttl}

                # the soa is the zone of itself, and the argument hostname
                if isinstance(rr, SOA):
                    zone = dict(object_type="DNSZone", hostname=record_hostname["name"])
                    zone_links[record_hostname["name"]] = zone
                    zone_links[input_hostname["name"]] = zone

                    soa = dict(
                        object_type="DNSSOARecord",
                        serial=rr.serial,
                        refresh=rr.refresh,
                        retry=rr.retry,
                        expire=rr.expire,
                        minimum=rr.minimum,
                        soa_hostname=register_hostname(str(rr.mname))["name"],
                        **default_args,
                    )
                    results.append(soa)

                if isinstance(rr, A):
                    ipv4 = dict(object_type="IPAddressV4", network=internet["name"], address=IPv4Address(str(rr)))
                    results.append(ipv4)
                    register_record(dict(object_type="DNSARecord", address=ipv4["address"], **default_args))

                if isinstance(rr, AAAA):
                    ipv6 = dict(object_type="IPAddressV6", network=internet["name"], address=IPv6Address(str(rr)))
                    results.append(ipv6)
                    register_record(dict(object_type="DNSAAAARecord", address=ipv6["address"], **default_args))

                if isinstance(rr, TXT):
                    # TODO: concatenated txt records should be handled better
                    # see https://www.rfc-editor.org/rfc/rfc1035 3.3.14
                    default_args["value"] = str(rr).strip('"').replace('" "', "")
                    register_record(dict(object_type="DNSTXTRecord", **default_args))

                if isinstance(rr, MX):
                    mail_hostname_reference = None
                    if str(rr.exchange) != ".":
                        mail_fqdn = register_hostname(str(rr.exchange))
                        mail_hostname_reference = mail_fqdn["name"]

                    register_record(
                        dict(object_type="DNSMXRecord", mail_hostname=mail_hostname_reference, preference=rr.preference, **default_args)
                    )

                if isinstance(rr, NS):
                    ns_fqdn = register_hostname(str(rr.target))
                    register_record(dict(object_type="DNSNSRecord", name_server_hostname=ns_fqdn["name"], **default_args))

                if isinstance(rr, CNAME):
                    target_fqdn = register_hostname(str(rr.target))
                    register_record(dict(object_type="DNSCNAMERecord", target_hostname=target_fqdn["name"], **default_args))

                if isinstance(rr, CAA):
                    record_value = str(rr).split(" ", 2)
                    default_args["flags"] = min(max(0, int(record_value[0])), 255)
                    default_args["tag"] = re.sub("[^\\w]", "", record_value[1].lower())
                    default_args["value"] = record_value[2]
                    register_record(dict(object_type="DNSCAARecord", **default_args))

    # link the hostnames to their discovered zones
    for hostname_, zone in zone_links.items():
        hostname_store[hostname_]["dns_zone"] = zone["hostname"]

    if zone:
        results.append(zone)

    results.extend(hostname_store.values())
    results.extend(record_store)

    # DKIM
    if dkim_results not in ["NXDOMAIN", "Timeout", "DNSSECFAIL"] and dkim_results.split("\n")[2] == "rcode NOERROR":
        results.append(dict(object_type="DKIMExists", hostname=input_hostname["name"]))

    # DMARC
    if dmarc_results not in ["NXDOMAIN", "Timeout"]:
        for rrset in from_text(dmarc_results).answer:
            for rr in rrset:
                if isinstance(rr, TXT):
                    results.append(dict(object_type="DMARCTXTRecord", hostname=input_hostname["name"], value=str(rr).strip('"'), ttl=rrset.ttl))

    return results


def get_parent_zone_soa(resolver: dns.resolver.Resolver, name: Name) -> Answer:
    while True:
        try:
            return resolver.resolve(name, dns.rdatatype.SOA)
        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
            pass

        try:
            name = name.parent()
        except dns.name.NoParent:
            raise ZoneNotFoundException


def get_email_security_records(resolver: dns.resolver.Resolver, hostname: str, record_subdomain: str) -> str:
    try:
        answer = resolver.resolve(f"{record_subdomain}.{hostname}", "TXT", raise_on_no_answer=False)
        if answer.rrset is None:
            return "NXDOMAIN"
        return answer.response.to_text()
    except dns.resolver.NoNameservers as error:
        # no servers responded happily, we'll check the response from the first
        # https://dnspython.readthedocs.io/en/latest/_modules/dns/rcode.html
        # https://www.rfc-editor.org/rfc/rfc8914#name-extended-dns-error-code-6-d
        firsterror = error.kwargs["errors"][0]
        if firsterror[3] == "SERVFAIL":
            edeerror = int(firsterror[4].options[0].code)
            if edeerror in (1, 2, 5, 6, 7, 8, 9, 10, 11, 12):  # DNSSEC error codes defined in RFC 8914
                return "DNSSECFAIL"  # returned when the resolver indicates a DNSSEC failure.
        raise  # Not dnssec related, unhandled, raise.
    except dns.resolver.NXDOMAIN:
        return "NXDOMAIN"
    except dns.resolver.Timeout:
        return "Timeout"


if __name__ == "__main__":
    result = run(sys.argv[1])
    print(result)
