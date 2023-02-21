from tools.domain_monitoring import MatchType, domains_match, tokenize_domain


def test_tokenize_domain():
    assert tokenize_domain("example.com") == ["example"]
    assert tokenize_domain("config.example.com") == ["config", "example"]
    assert tokenize_domain("www.nu.nl") == ["nu"]


def test_domain_match_direct_simple():
    assert domains_match({"vws.nl"}, ["vws.nl"]) == [(MatchType.DIRECT, "vws.nl", "vws.nl")]


def test_domain_match_direct_subdomain():
    assert domains_match({"vws.nl"}, ["vws.freehosting.net"]) == [(MatchType.DIRECT, "vws.nl", "vws.freehosting.net")]


def test_domain_match_direct_multiple():
    assert domains_match({"example.com"}, ["example.com", "example.org"]) == [
        (MatchType.DIRECT, "example.com", "example.com"),
        (MatchType.DIRECT, "example.com", "example.org"),
    ]
    assert domains_match({"coronamelder.nl", "test.nl"}, ["coronamelder.nl", "coronamelder.net", "test.com"]) == [
        (MatchType.DIRECT, "test.nl", "test.com"),
        (MatchType.DIRECT, "coronamelder.nl", "coronamelder.nl"),
        (MatchType.DIRECT, "coronamelder.nl", "coronamelder.net"),
    ]


def test_domain_match_substring_simple():
    assert domains_match({"vws.nl"}, ["mijnvws.net"]) == [(MatchType.SUBSTRING, "vws.nl", "mijnvws.net")]


def test_domain_match_substring_subdomain():
    assert domains_match({"vws.nl"}, ["vwss.inloggen.nl"]) == [(MatchType.SUBSTRING, "vws.nl", "vwss.inloggen.nl")]


def test_domain_match_substring_multiple():
    assert domains_match({"example.com"}, ["sub.example.com", "exampledata.org"]) == [
        (MatchType.DIRECT, "example.com", "sub.example.com"),
        (MatchType.SUBSTRING, "example.com", "exampledata.org"),
    ]

    assert domains_match({"coronamelder.nl"}, ["coronamelder.nl", "coronamelder.net", "mijncoronamelder.tk"]) == [
        (MatchType.DIRECT, "coronamelder.nl", "coronamelder.nl"),
        (MatchType.DIRECT, "coronamelder.nl", "coronamelder.net"),
        (MatchType.SUBSTRING, "coronamelder.nl", "mijncoronamelder.tk"),
    ]
