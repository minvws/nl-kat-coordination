import pytest

from tools.domain_monitoring import MatchType, clean_input_domain, domains_match, tokenize_domain


def test_tokenize_domain():
    assert tokenize_domain("example.com") == ["example"]
    assert tokenize_domain("config.example.com") == ["config", "example"]
    assert tokenize_domain("www.nu.nl") == ["nu"]


def test_clean_input_domain():
    assert clean_input_domain("example.com") == {"example"}
    assert clean_input_domain("config.example.com") == {"config", "example"}


def test_domain_match_direct_simple():
    assert domains_match({"vws.nl"}, ["vws.nl"]) == [(MatchType.DIRECT, "vws.nl")]


def test_domain_match_direct_subdomain():
    assert domains_match({"vws.nl"}, ["vws.freehosting.net"]) == [(MatchType.DIRECT, "vws.freehosting.net")]


def test_domain_match_direct_multiple():
    assert domains_match({"example.com"}, ["example.com", "example.org"]) == [
        (MatchType.DIRECT, "example.com"),
        (MatchType.DIRECT, "example.org"),
    ]


def test_domain_match_substring_simple():
    assert domains_match({"vws.nl"}, ["mijnvws.net"]) == [(MatchType.SUBSTRING, "mijnvws.net")]


def test_domain_match_substring_subdomain():
    assert domains_match({"vws.nl"}, ["vwss.inloggen.nl"]) == [(MatchType.SUBSTRING, "vwss.inloggen.nl")]


def test_domain_match_substring_multiple():
    assert domains_match({"example.com"}, ["sub.example.com", "exampledata.org"]) == [
        (MatchType.DIRECT, "sub.example.com"),
        (MatchType.SUBSTRING, "exampledata.org"),
    ]

    assert domains_match({"coronamelder.nl"}, ["coronamelder.nl", "coronamelder.net", "mijncoronamelder.tk"]) == [
        (MatchType.DIRECT, "coronamelder.nl"),
        (MatchType.DIRECT, "coronamelder.net"),
        (MatchType.SUBSTRING, "mijncoronamelder.tk"),
    ]
