"""Network-free regressions for the kat_dns boefje and normalizer."""

import json

import dns.edns
import dns.message
import dns.rcode
import dns.resolver
import dns.rrset
import pytest

from boefjes.plugins.kat_dns import main, normalize
from octopoes.models.ooi.dns.records import DNSCAARecord, DNSTXTRecord
from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.ooi.email_security import DMARCTXTRecord
from octopoes.models.ooi.network import Network


def dns_response(name: str, type_: str, *records: str, ttl: int = 60) -> dns.message.Message:
    response = dns.message.make_response(dns.message.make_query(name, type_))
    if records:
        response.answer.append(dns.rrset.from_text(name, ttl, "IN", type_, *records))
    return response


def normalizer_results(
    *,
    hostname: str = "example.org",
    records: list[dns.message.Message] | None = None,
    dmarc_response: str = "NXDOMAIN",
    dkim_response: str = "NXDOMAIN",
) -> list:
    input_hostname = Hostname(network=Network(name="internet").reference, name=hostname)
    dns_records = "\n\n".join(f"RESOLVER: 1.1.1.1\n{r.to_text()}" for r in (records or []))
    raw = json.dumps(
        {"dns_records": dns_records, "dmarc_response": dmarc_response, "dkim_response": dkim_response}
    ).encode()
    return list(normalize.run(input_hostname.serialize(), raw))


@pytest.mark.parametrize(
    ("dmarc", "dkim", "expected_timeout"),
    [("Timeout", "NOANSWER", False), ("NOANSWER", "Timeout", False), ("Timeout", "Timeout", True)],
)
def test_timeout_requires_both_email_queries_and_no_records(monkeypatch, dmarc, dkim, expected_timeout):
    """#1: a DMARC timeout alone must not masquerade as a total timeout."""
    monkeypatch.setattr(main, "get_record_types", lambda: {"A"})
    monkeypatch.setattr(
        dns.resolver.Resolver, "resolve", lambda *a, **k: (_ for _ in ()).throw(dns.resolver.NoAnswer())
    )
    monkeypatch.setattr(
        main,
        "get_email_security_records",
        lambda resolver, hostname, subdomain: dmarc if subdomain == "_dmarc" else dkim,
    )
    meta = {"arguments": {"input": {"name": "example.org"}}}
    if expected_timeout:
        with pytest.raises(main.TimeoutException):
            main.run(meta)
    else:
        assert json.loads(main.run(meta)[0][1])["dkim_response"] == dkim


def test_dnssecfail_dmarc_is_skipped():
    """#2: the sentinel is not a textual DNS message."""
    assert not any(isinstance(result, DMARCTXTRecord) for result in normalizer_results(dmarc_response="DNSSECFAIL"))


def test_dmarc_ede_option_is_ignored_without_losing_txt():
    """#4: dnspython's from_text cannot parse EDE header lines."""
    response = dns_response("_dmarc.example.org", "TXT", '"v=DMARC1; p=reject"')
    text = response.to_text().replace(";QUESTION", "option EDE 18 (Prohibited)\n;QUESTION")
    records = [obj for obj in normalizer_results(dmarc_response=text) if isinstance(obj, DMARCTXTRecord)]
    assert len(records) == 1
    assert records[0].value == "v=DMARC1; p=reject"
    assert records[0].ttl == 60


def test_invalid_dmarc_text_does_not_abort_records():
    records = normalizer_results(
        records=[dns_response("example.org", "TXT", '"ordinary value"')], dmarc_response="not a DNS response"
    )
    assert any(isinstance(obj, DNSTXTRecord) for obj in records)


def no_nameservers_error(response: dns.message.Message, request: dns.message.Message) -> dns.resolver.NoNameservers:
    return dns.resolver.NoNameservers(request=request, errors=[("1.1.1.1", False, 53, "SERVFAIL", response)])


def test_servfail_without_ede_returns_sentinel(monkeypatch):
    """#5: SERVFAIL without EDNS options must not cause IndexError."""
    request = dns.message.make_query("_dmarc.example.org", "TXT")
    response = dns.message.make_response(request)
    response.set_rcode(dns.rcode.SERVFAIL)
    response.use_edns(edns=0, options=[])
    error = no_nameservers_error(response, request)
    monkeypatch.setattr(dns.resolver.Resolver, "resolve", lambda *a, **k: (_ for _ in ()).throw(error))
    assert main.get_email_security_records(dns.resolver.Resolver(), "example.org", "_dmarc") == "SERVFAIL"
    assert not any(isinstance(obj, DMARCTXTRecord) for obj in normalizer_results(dmarc_response="SERVFAIL"))


def test_dnssec_ede_can_follow_another_option(monkeypatch):
    """#5: do not assume options[0] is an EDE option."""
    request = dns.message.make_query("_dmarc.example.org", "TXT")
    response = dns.message.make_response(request)
    response.set_rcode(dns.rcode.SERVFAIL)
    response.use_edns(edns=0, options=[dns.edns.GenericOption(dns.edns.OptionType.NSID, b"x"), dns.edns.EDEOption(6)])
    error = no_nameservers_error(response, request)
    monkeypatch.setattr(dns.resolver.Resolver, "resolve", lambda *a, **k: (_ for _ in ()).throw(error))
    assert main.get_email_security_records(dns.resolver.Resolver(), "example.org", "_dmarc") == "DNSSECFAIL"


def test_unknown_caa_tag_preserved():
    """#6: RFC 8659 CAA property tags are extensible."""
    records = normalizer_results(records=[dns_response("example.org", "CAA", '0 customtag "ca.example.net"')])
    caa = [obj for obj in records if isinstance(obj, DNSCAARecord)]
    assert len(caa) == 1
    assert caa[0].tag == "customtag"
    assert caa[0].flags == 0


def test_binary_txt_octets_are_escaped():
    """#7: a TXT RR contains arbitrary bytes, not necessarily UTF-8."""
    records = normalizer_results(records=[dns_response("example.org", "TXT", r'"prefix\255suffix"')])
    txt = [obj for obj in records if isinstance(obj, DNSTXTRecord)]
    assert len(txt) == 1
    assert txt[0].value == r"prefix\377suffix"


def test_binary_txt_chunks_join_before_utf8_decode():
    """#7: a UTF-8 codepoint can straddle TXT character-string boundaries."""
    records = normalizer_results(records=[dns_response("example.org", "TXT", r'"caf\195" "\169"')])
    assert [obj.value for obj in records if isinstance(obj, DNSTXTRecord)] == ["café"]


def test_multipart_dmarc_txt_is_concatenated():
    """#9: multiple TXT character-strings join without quote separators."""
    response = dns_response("_dmarc.example.org", "TXT", '"v=DMARC1;p=" "reject;rua=mailto:a@example.org"')
    records = [obj for obj in normalizer_results(dmarc_response=response.to_text()) if isinstance(obj, DMARCTXTRecord)]
    assert len(records) == 1
    assert records[0].value == "v=DMARC1;p=reject;rua=mailto:a@example.org"
