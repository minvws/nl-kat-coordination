from bits.cookie_parser.cookie_parser import run
from octopoes.models import Reference
from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.ooi.findings import KATFindingType, Finding
from octopoes.models.ooi.network import Network
from octopoes.models.ooi.web import RawCookie, Cookie


def test_spf_discovery_simple_success():
    raw_cookie = RawCookie(
        raw="has_recent_activity=1; path=/; expires=Tue, 28 Feb 2023 14:21:36 GMT; secure; HttpOnly; SameSite=Lax, gh_sess=xxxxxxx; path=/; secure; HttpOnly; SameSite=Lax",
        response_domain=Hostname(name="domain.com", network=Network(name="internet").reference).reference,
    )
    results = list(run(raw_cookie, []))

    cookies = [result for result in results if isinstance(result, Cookie)]
    assert len(cookies) == 2
    hostnames = [result for result in results if isinstance(result, Hostname)]
    assert len(hostnames) == 2

    assert cookies[0].same_site == cookies[1].same_site == "Lax"

    # cant check created because its generated at runtime
    assert cookies[0].dict() == {
        "object_type": "Cookie",
        "scan_profile": None,
        "primary_key": "Cookie|has_recent_activity|1|internet|domain.com|/",
        "name": "has_recent_activity",
        "value": "1",
        "expires": "2023-02-28 14:21:36",
        "max_age": None,
        "domain": Reference("Hostname|internet|domain.com"),
        "path": "/",
        "created": cookies[0].created,
        "persistent": True,
        "host_only": True,
        "secure_only": True,
        "http_only": True,
        "same_site": "Lax",
    }


def test_spf_discovery_simple_invalid():
    raw_cookie = RawCookie(
        raw="has_recent_activity=1; path=/; expires=sdsd, 28 Feb 2023 14:21:36 GMT; secure; HttpOnly; SameSite=Lax, gh_sess=xxxxxxx; path=/; secure; HttpOnly; SameSite=Lax",
        response_domain=Hostname(name="domain.com", network=Network(name="internet").reference).reference,
    )
    results = list(run(raw_cookie, []))

    assert isinstance(results[0], KATFindingType)
    assert isinstance(results[1], Finding)


def test_spf_discovery_simple_invalid2():
    raw_cookie = RawCookie(
        raw="has_recent_activity=1; path=/; expires=Tue, 28 Feb 2023 14:21:36 GMT; secure; HttpOnly; Nonsense; SameSite=Lax, gh_sess=xxxxxxx; path=/; secure; HttpOnly; SameSite=Lax",
        response_domain=Hostname(name="domain.com", network=Network(name="internet").reference).reference,
    )
    results = list(run(raw_cookie, []))

    assert isinstance(results[0], KATFindingType)
    assert isinstance(results[1], Finding)
