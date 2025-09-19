import json
import os
import re
import sys
from collections import defaultdict
from os import getenv

import dns
import httpx
from dns.edns import EDEOption
from dns.message import from_text
from dns.rdtypes.ANY.CAA import CAA
from dns.rdtypes.ANY.CNAME import CNAME
from dns.rdtypes.ANY.MX import MX
from dns.rdtypes.ANY.NS import NS
from dns.rdtypes.ANY.TXT import TXT
from dns.rdtypes.IN.A import A
from dns.rdtypes.IN.AAAA import AAAA
from dns.resolver import Answer

DEFAULT_RECORD_TYPES = {"A", "AAAA", "CAA", "CERT", "RP", "SRV", "TXT", "MX", "NS", "CNAME", "DNAME"}


class TimeoutException(Exception):
    pass


class ZoneNotFoundException(Exception):
    pass


def get_record_types(arg: str) -> set[str]:
    parsed_requested_record_types = map(lambda x: re.sub(r"[^A-Za-z]", "", x), arg.upper().split(","))
    return set(parsed_requested_record_types).intersection(DEFAULT_RECORD_TYPES)


def run(hostname: str, record_types: set[str], internet_id: int) -> list:
    resolver = dns.resolver.Resolver()

    # https://dnspython.readthedocs.io/en/stable/_modules/dns/edns.html
    # enable EDE to get the DNSSEC Bogus return values if the server supports it # codespell-ignore
    resolver.use_edns(options=[EDEOption(15)])
    nameserver = getenv("REMOTE_NS", "1.1.1.1")
    resolver.nameservers = [nameserver]

    answers = []
    for type_ in record_types:
        try:
            answer: Answer = resolver.resolve(hostname, type_)
            answers.append(answer)
        except (dns.resolver.NoAnswer, dns.resolver.Timeout):
            pass
        except dns.resolver.NXDOMAIN:
            return []

    dmarc_results = get_email_security_records(resolver, hostname, "_dmarc")
    dkim_results = get_email_security_records(resolver, hostname, "_domainkey")

    if not answers and dmarc_results == "Timeout" and dkim_results == "Timeout":
        raise TimeoutException("No answers from DNS-Server due to timeouts.")

    hostname_store = {}
    record_store = []

    def register_hostname(name: str) -> dict:
        hostname = {"object_type": "Hostname", "network": internet_id, "name": name.rstrip(".")}
        hostname_store[hostname["name"]] = hostname
        return hostname

    def register_record(record: dict) -> dict:
        record_store.append(record)
        return record

    # register argument hostname
    input_hostname = register_hostname(hostname)

    results = []

    for answer in answers:
        for rrset in answer.response.answer:
            for rr in rrset:
                record_hostname = register_hostname(str(rrset.name))
                default_args = {"hostname": record_hostname["name"], "value": str(rr), "ttl": rrset.ttl}

                if isinstance(rr, A):
                    ipv4 = {"object_type": "IPAddress", "network": internet_id, "address": str(rr)}
                    results.append(ipv4)
                    register_record({"object_type": "DNSARecord", "ip_address": ipv4["address"], **default_args})

                if isinstance(rr, AAAA):
                    ipv6 = {"object_type": "IPAddress", "network": internet_id, "address": str(rr)}
                    results.append(ipv6)
                    register_record({"object_type": "DNSAAAARecord", "ip_address": ipv6["address"], **default_args})

                if isinstance(rr, TXT):
                    # TODO: concatenated txt records should be handled better
                    # see https://www.rfc-editor.org/rfc/rfc1035 3.3.14
                    default_args["value"] = str(rr).strip('"').replace('" "', "")
                    register_record({"object_type": "DNSTXTRecord", **default_args})

                if isinstance(rr, MX):
                    mail_hostname_reference = None
                    if str(rr.exchange) != ".":
                        mail_fqdn = register_hostname(str(rr.exchange))
                        mail_hostname_reference = mail_fqdn["name"]

                    register_record(
                        {
                            "object_type": "DNSMXRecord",
                            "mail_hostname": mail_hostname_reference,
                            "preference": rr.preference,
                            **default_args,
                        }
                    )

                if isinstance(rr, NS):
                    ns_fqdn = register_hostname(str(rr.target))
                    register_record({"object_type": "DNSNSRecord", "name_server": ns_fqdn["name"], **default_args})

                if isinstance(rr, CNAME):
                    target_fqdn = register_hostname(str(rr.target))
                    register_record({"object_type": "DNSCNAMERecord", "target": target_fqdn["name"], **default_args})

                if isinstance(rr, CAA):
                    record_value = str(rr).split(" ", 2)
                    default_args["flags"] = min(max(0, int(record_value[0])), 255)
                    default_args["tag"] = re.sub("[^\\w]", "", record_value[1].lower())
                    default_args["value"] = record_value[2]
                    register_record({"object_type": "DNSCAARecord", **default_args})

    results.extend(hostname_store.values())
    results.extend(record_store)

    # DKIM
    if dkim_results not in ["NXDOMAIN", "Timeout", "DNSSECFAIL"] and dkim_results.split("\n")[2] == "rcode NOERROR":
        results.append({"object_type": "DKIMExists", "hostname": input_hostname["name"]})

    # DMARC
    if dmarc_results not in ["NXDOMAIN", "Timeout"]:
        for rrset in from_text(dmarc_results).answer:
            for rr in rrset:
                if isinstance(rr, TXT):
                    results.append(
                        {
                            "object_type": "DNSTXTRecord",
                            "hostname": input_hostname["name"],
                            "value": str(rr).strip('"'),
                            "ttl": rrset.ttl,
                        }
                    )

    return results


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
    token = os.getenv("OPENKAT_TOKEN")
    if not token:
        raise Exception("No OPENKAT_TOKEN env variable")

    base_url = os.getenv("OPENKAT_API")
    if not base_url:
        raise Exception("No OPENKAT_API env variable")

    headers = {"Authorization": "Token " + token}
    client = httpx.Client(base_url=base_url, headers=headers)
    response = client.get("/objects/network/", params={"name": "internet", "limit": 1}).json()

    if not response["results"]:
        internet = client.post("/objects/network/", json={"name": "internet"}).json()
    else:
        internet = response["results"][0]

    record_types = DEFAULT_RECORD_TYPES if len(sys.argv) < 3 else get_record_types(sys.argv[2])
    results = run(sys.argv[1], record_types, internet["id"])
    results_grouped = defaultdict(list)
    for result in results:
        results_grouped[result.pop("object_type").lower()].append(result)

    hostnames = client.post("/objects/hostname/", headers=headers, json=results_grouped["hostname"]).json()
    by_name = {h["name"]: h["id"] for h in hostnames}

    ips = client.post("/objects/ipaddress/", headers=headers, json=results_grouped["ipaddress"]).json()
    by_address = {ip["address"]: ip["id"] for ip in ips}

    for object_path, objects in results_grouped.items():
        for obj in objects:
            if "hostname" in obj:
                obj["hostname"] = by_name[obj["hostname"]]
            if "mail_server" in obj:
                obj["mail_server"] = by_name[obj["mail_server"]]
            if "name_server" in obj:
                obj["name_server"] = by_name[obj["name_server"]]
            if "target" in obj:
                obj["target"] = by_name[obj["target"]]

            if "ip_address" in obj:
                obj["ip_address"] = by_address[obj["ip_address"]]

        res = client.post("/objects/{object_path}/", headers=headers, json=objects)

    print(json.dumps(results))  # noqa: T201
