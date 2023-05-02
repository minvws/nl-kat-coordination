import pytest

from octopoes.models.ooi.findings import Finding
from octopoes.models.ooi.network import IPAddress, IPPort, Network
from octopoes.models.path import Path
from octopoes.xtdb.query import InvalidField, Query


def test_basic_field_where_clause():
    query = Query(Network).where(Network, name="test")
    assert query.format() == """
{:query {:find [(pull Network [*])] :where [
    [ Network :Network/name "test" ]
    [ Network :object_type "Network" ]]}}
"""

    query = query.limit(4)
    assert query.format() == """
{:query {:find [(pull Network [*])] :where [
    [ Network :Network/name "test" ]
    [ Network :object_type "Network" ]] :limit 4}}
"""
    query = query.offset(0)
    assert query.format() == """
{:query {:find [(pull Network [*])] :where [
    [ Network :Network/name "test" ]
    [ Network :object_type "Network" ]] :limit 4 :offset 0}}
"""


def test_reference_field_where_clause():
    query = Query(Network).where(Finding, ooi=Network)
    assert query.format() == """
{:query {:find [(pull Network [*])] :where [
    [ Finding :Finding/ooi Network ]
    [ Finding :object_type "Finding" ]
    [ Network :object_type "Network" ]]}}
"""


def test_remove_duplicates():
    query = Query(Network).where(Finding, ooi=Network)
    assert query == query.where(Finding, ooi=Network)


def test_invalid_fields_name():
    with pytest.raises(InvalidField) as ctx:
        Query(Network).where(Network, ooi=Finding)

    assert ctx.exconly() == 'octopoes.xtdb.query.InvalidField: "ooi" is not a field of Network'

    with pytest.raises(InvalidField) as ctx:
        Query(Network).where(Network, abc="def")

    assert ctx.exconly() == 'octopoes.xtdb.query.InvalidField: "abc" is not a field of Network'


def test_escaping_quotes():
    query = Query(Network).where(Finding, ooi=Network).where(Network, name='test " name')
    assert query.format() == """
{:query {:find [(pull Network [*])] :where [
    [ Finding :Finding/ooi Network ]
    [ Finding :object_type "Finding" ]
    [ Network :Network/name "test \\" name" ]
    [ Network :object_type "Network" ]]}}
"""

def test_invalid_field_types():
    with pytest.raises(InvalidField) as ctx:
        Query(Network).where(Finding, ooi=3)

    assert ctx.exconly() == "octopoes.xtdb.query.InvalidField: value '3' should be a string or an OOI Type"

    with pytest.raises(InvalidField) as ctx:
        Query(Network).where(Finding, ooi=InvalidField)

    assert ctx.exconly() == "octopoes.xtdb.query.InvalidField: <class 'octopoes.xtdb.query.InvalidField'> is not an OOI"

    with pytest.raises(InvalidField) as ctx:
        Query(Network).where(Network, name=Network)

    assert ctx.exconly() == 'octopoes.xtdb.query.InvalidField: "name" is not a relation of Network'


def test_allow_string_for_foreign_keys():
    query = Query(Network).where(Finding, ooi="Network|internet")

    assert query.format() == """
{:query {:find [(pull Network [*])] :where [
    [ Finding :Finding/ooi "Network|internet" ]
    [ Finding :object_type "Finding" ]
    [ Network :object_type "Network" ]]}}
"""


def test_big_multiple_direction_query():
    query = (
        Query(Finding)
        .where(Finding, ooi=Network, finding_type="KATFindingType|KAT-500")
        .where(IPAddress, network=Network)
        .where(IPPort, address=IPAddress)
        .where(IPPort, primary_key="IPPort|internet|xxx:xxx:x|tcp|23")
    )

    assert (
        query.format()
        == """
{:query {:find [(pull Finding [*])] :where [
    (or [ IPAddress :IPAddressV4/network Network ] [ IPAddress :IPAddressV6/network Network ] )
    [ Finding :Finding/finding_type "KATFindingType|KAT-500" ]
    [ Finding :Finding/ooi Network ]
    [ Finding :object_type "Finding" ]
    [ IPAddress :object_type "IPAddress" ]
    [ IPPort :IPPort/address IPAddress ]
    [ IPPort :IPPort/primary_key "IPPort|internet|xxx:xxx:x|tcp|23" ]
    [ IPPort :object_type "IPPort" ]]}}
"""
    )


def test_create_query_from_relation_path():
    query = Query.from_path(Path.parse("HTTPHeader.resource.website.hostname.network.<ooi [is Finding]"))

    assert (
        query.format()
        == """
{:query {:find [(pull Finding [*])] :where [
    [ Finding :Finding/ooi Network ]
    [ Finding :object_type "Finding" ]
    [ HTTPHeader :HTTPHeader/resource HTTPResource ]
    [ HTTPHeader :object_type "HTTPHeader" ]
    [ HTTPResource :HTTPResource/website Website ]
    [ HTTPResource :object_type "HTTPResource" ]
    [ Hostname :Hostname/network Network ]
    [ Hostname :object_type "Hostname" ]
    [ Website :Website/hostname Hostname ]
    [ Website :object_type "Website" ]]}}
"""
    )

    query = Query.from_path(Path.parse("IPPort.address.network.<ooi [is Finding]")).where(
        IPPort, primary_key="IPPort|internet|xxx:xxx:x|tcp|23"
    )
    assert (
        query.format()
        == """
{:query {:find [(pull Finding [*])] :where [
    (or [ IPAddress :IPAddressV4/network Network ] [ IPAddress :IPAddressV6/network Network ] )
    [ Finding :Finding/ooi Network ]
    [ Finding :object_type "Finding" ]
    [ IPAddress :object_type "IPAddress" ]
    [ IPPort :IPPort/address IPAddress ]
    [ IPPort :IPPort/primary_key "IPPort|internet|xxx:xxx:x|tcp|23" ]
    [ IPPort :object_type "IPPort" ]]}}
"""
    )
