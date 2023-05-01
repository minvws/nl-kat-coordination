import pytest

from octopoes.models.ooi.findings import Finding
from octopoes.models.ooi.network import IPAddress, IPPort, Network
from octopoes.models.path import Path
from octopoes.xtdb.query import InvalidField, Query


def test_basic_field_where_clause():
    assert (
        str(Query(Network).where(Network, name="test"))
        == '{:query {:find [(pull Network [*])] :where [ [ Network :Network/name "test" ]]}}'
    )


def test_reference_field_where_clause():
    assert (
        str(Query(Network).where(Finding, ooi=Network))
        == "{:query {:find [(pull Network [*])] :where [ [ Finding :Finding/ooi Network ]]}}"
    )


def test_invalid_fields_name():
    with pytest.raises(InvalidField) as ctx:
        Query(Network).where(Network, ooi=Finding)

    assert ctx.exconly() == 'octopoes.xtdb.query.InvalidField: "ooi" is not a field of Network'

    with pytest.raises(InvalidField) as ctx:
        Query(Network).where(Network, abc="def")

    assert ctx.exconly() == 'octopoes.xtdb.query.InvalidField: "abc" is not a field of Network'


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
    assert (
        str(Query(Network).where(Finding, ooi="Network|internet"))
        == '{:query {:find [(pull Network [*])] :where [ [ Finding :Finding/ooi "Network|internet" ]]}}'
    )


def test_big_multiple_direction_query():
    query = (
        Query(Finding)
        .where(Finding, ooi=Network, finding_type="KATFindingType|KAT-500")
        .where(Finding, ooi=Network)
        .where(IPAddress, network=Network)
        .where(IPPort, address=IPAddress)
        .where(IPPort, primary_key="IPPort|internet|xxx:xxx:x|tcp|23")
    )

    assert (
        query.format()
        == """
{:query {:find [(pull Finding [*])] :where [
    [ Finding :Finding/ooi Network ]
    [ Finding :Finding/finding_type "KATFindingType|KAT-500" ]
    [ Finding :Finding/ooi Network ]
    (or [ IPAddress :IPAddressV4/network Network ] [ IPAddress :IPAddressV6/network Network ] )
    [ IPPort :IPPort/address IPAddress ]
    [ IPPort :IPPort/primary_key "IPPort|internet|xxx:xxx:x|tcp|23" ]]}}
"""
    )


def test_create_query_from_relation_path():
    query = Query.from_path(Path.parse("HTTPHeader.resource.website.hostname.network.<ooi [is Finding]"))

    assert (
        query.format()
        == """
{:query {:find [(pull Finding [*])] :where [
    [ HTTPHeader :HTTPHeader/resource HTTPResource ]
    [ HTTPResource :HTTPResource/website Website ]
    [ Website :Website/hostname Hostname ]
    [ Hostname :Hostname/network Network ]
    [ Finding :Finding/ooi Network ]]}}
"""
    )

    query = Query.from_path(Path.parse("IPPort.address.network.<ooi [is Finding]")).where(
        IPPort, primary_key="IPPort|internet|xxx:xxx:x|tcp|23"
    )

    assert (
        query.format()
        == """
{:query {:find [(pull Finding [*])] :where [
    [ IPPort :IPPort/address IPAddress ]
    (or [ IPAddress :IPAddressV4/network Network ] [ IPAddress :IPAddressV6/network Network ] )
    [ Finding :Finding/ooi Network ]
    [ IPPort :IPPort/primary_key "IPPort|internet|xxx:xxx:x|tcp|23" ]]}}
"""
    )
