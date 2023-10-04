from uuid import UUID

import pytest

from octopoes.models.ooi.dns.records import DNSAAAARecord, DNSNSRecord
from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.ooi.findings import Finding, FindingType
from octopoes.models.ooi.network import IPAddress, IPPort, Network
from octopoes.models.ooi.web import Website
from octopoes.models.path import Path
from octopoes.xtdb.query import A, InvalidField, Query


def test_basic_field_where_clause():
    query = Query(Network).where(Network, name="test")
    assert (
        query.format()
        == """{:query {:find [(pull Network [*])] :where [
    [ Network :Network/name "test" ]
    [ Network :object_type "Network" ]]}}"""
    )

    query = query.limit(4)
    assert (
        query.format()
        == """{:query {:find [(pull Network [*])] :where [
    [ Network :Network/name "test" ]
    [ Network :object_type "Network" ]] :limit 4}}"""
    )
    query = query.offset(0)
    assert (
        query.format()
        == """{:query {:find [(pull Network [*])] :where [
    [ Network :Network/name "test" ]
    [ Network :object_type "Network" ]] :limit 4 :offset 0}}"""
    )


def test_reference_field_where_clause():
    query = Query(Network).where(Finding, ooi=Network)
    assert (
        query.format()
        == """{:query {:find [(pull Network [*])] :where [
    [ Finding :Finding/ooi Network ]
    [ Finding :object_type "Finding" ]
    [ Network :object_type "Network" ]]}}"""
    )


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
    assert (
        query.format()
        == """{:query {:find [(pull Network [*])] :where [
    [ Finding :Finding/ooi Network ]
    [ Finding :object_type "Finding" ]
    [ Network :Network/name "test \\" name" ]
    [ Network :object_type "Network" ]]}}"""
    )


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

    assert (
        query.format()
        == """{:query {:find [(pull Network [*])] :where [
    [ Finding :Finding/ooi "Network|internet" ]
    [ Finding :object_type "Finding" ]
    [ Network :object_type "Network" ]]}}"""
    )


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
        == """{:query {:find [(pull Finding [*])] :where [
    (or [ IPAddress :IPAddressV4/network Network ] [ IPAddress :IPAddressV6/network Network ] )
    (or [ IPAddress :object_type "IPAddressV4" ] [ IPAddress :object_type "IPAddressV6" ] )
    [ Finding :Finding/finding_type "KATFindingType|KAT-500" ]
    [ Finding :Finding/ooi Network ]
    [ Finding :object_type "Finding" ]
    [ IPPort :IPPort/address IPAddress ]
    [ IPPort :IPPort/primary_key "IPPort|internet|xxx:xxx:x|tcp|23" ]
    [ IPPort :object_type "IPPort" ]]}}"""
    )


def test_create_query_from_path():
    query = Query.from_path(Path.parse("HTTPHeader.resource.website.hostname.network.<ooi [is Finding]"))

    assert (
        query.format()
        == """{:query {:find [(pull Finding [*])] :where [
    [ Finding :Finding/ooi Network ]
    [ Finding :object_type "Finding" ]
    [ HTTPHeader :HTTPHeader/resource HTTPResource ]
    [ HTTPHeader :object_type "HTTPHeader" ]
    [ HTTPResource :HTTPResource/website Website ]
    [ HTTPResource :object_type "HTTPResource" ]
    [ Hostname :Hostname/network Network ]
    [ Hostname :object_type "Hostname" ]
    [ Website :Website/hostname Hostname ]
    [ Website :object_type "Website" ]]}}"""
    )

    query = Query.from_path(Path.parse("IPPort.address.network.<ooi [is Finding]")).where(
        IPPort, primary_key="IPPort|internet|xxx:xxx:x|tcp|23"
    )
    assert (
        query.format()
        == """{:query {:find [(pull Finding [*])] :where [
    (or [ IPAddress :IPAddressV4/network Network ] [ IPAddress :IPAddressV6/network Network ] )
    (or [ IPAddress :object_type "IPAddressV4" ] [ IPAddress :object_type "IPAddressV6" ] )
    [ Finding :Finding/ooi Network ]
    [ Finding :object_type "Finding" ]
    [ IPPort :IPPort/address IPAddress ]
    [ IPPort :IPPort/primary_key "IPPort|internet|xxx:xxx:x|tcp|23" ]
    [ IPPort :object_type "IPPort" ]]}}"""
    )


def test_finding_type_count_query():
    query = Query(FindingType).where(Finding, finding_type=FindingType).group_by(FindingType).count(Finding)
    object_type_options = [
        '[ FindingType :object_type "ADRFindingType" ]',
        '[ FindingType :object_type "CAPECFindingType" ]',
        '[ FindingType :object_type "CVEFindingType" ]',
        '[ FindingType :object_type "CWEFindingType" ]',
        '[ FindingType :object_type "KATFindingType" ]',
        '[ FindingType :object_type "RetireJSFindingType" ]',
        '[ FindingType :object_type "SnykFindingType" ]',
    ]
    or_statement_list = " ".join(object_type_options)

    assert (
        query.format()
        == f"""{{:query {{:find [(pull FindingType [*]) (count Finding)] :where [
    (or {or_statement_list} )
    [ Finding :Finding/finding_type FindingType ]
    [ Finding :object_type "Finding" ]]}}}}"""
    )


def test_create_query_from_path_abstract():
    path = Path.parse("IPAddress.<address[is IPPort]")

    query = Query.from_path(path).where(IPAddress, primary_key="test_pk")

    expected_query = """{:query {:find [(pull IPPort [*])] :where [
    (or [ IPAddress :IPAddressV4/primary_key "test_pk" ] [ IPAddress :IPAddressV6/primary_key "test_pk" ] )
    (or [ IPAddress :object_type "IPAddressV4" ] [ IPAddress :object_type "IPAddressV6" ] )
    [ IPPort :IPPort/address IPAddress ]
    [ IPPort :object_type "IPPort" ]]}}"""

    assert query.format() == expected_query


def test_aliased_query():
    h1 = A(Hostname, UUID("4b4afa7e-5b76-4506-a373-069216b051c2"))
    h2 = A(Hostname, UUID("98076f7a-7606-47ac-85b7-b511ee21ae42"))
    query = (
        Query(DNSAAAARecord)
        .where(DNSAAAARecord, hostname=h1)
        .where(DNSNSRecord, hostname=h1)
        .where(DNSNSRecord, name_server_hostname=h2)
        .where(Website, hostname=h2)
        .where(Website, primary_key="test_pk")
    )

    expected_query = """{:query {:find [(pull DNSAAAARecord [*])] :where [
    [ DNSAAAARecord :DNSAAAARecord/hostname ?4b4afa7e-5b76-4506-a373-069216b051c2 ]
    [ DNSAAAARecord :object_type "DNSAAAARecord" ]
    [ DNSNSRecord :DNSNSRecord/hostname ?4b4afa7e-5b76-4506-a373-069216b051c2 ]
    [ DNSNSRecord :DNSNSRecord/name_server_hostname ?98076f7a-7606-47ac-85b7-b511ee21ae42 ]
    [ DNSNSRecord :object_type "DNSNSRecord" ]
    [ Website :Website/hostname ?98076f7a-7606-47ac-85b7-b511ee21ae42 ]
    [ Website :Website/primary_key "test_pk" ]
    [ Website :object_type "Website" ]]}}"""

    assert query.format() == expected_query


def test_aliased_path_query(mocker):
    """Traverse the Hostname object twice"""

    mocker.patch("octopoes.xtdb.query.uuid4", return_value=UUID("311d6399-4bb4-4830-b077-661cc3f4f2c1"))
    path = Path.parse("Website.hostname.<hostname[is DNSNSRecord].name_server_hostname.<hostname[is DNSAAAARecord]")
    query = Query.from_path(path).where(Website, primary_key="test_pk")

    expected_query = """{:query {:find [(pull DNSAAAARecord [*])] :where [
    [ DNSAAAARecord :DNSAAAARecord/hostname ?311d6399-4bb4-4830-b077-661cc3f4f2c1 ]
    [ DNSAAAARecord :object_type "DNSAAAARecord" ]
    [ DNSNSRecord :DNSNSRecord/hostname Hostname ]
    [ DNSNSRecord :DNSNSRecord/name_server_hostname ?311d6399-4bb4-4830-b077-661cc3f4f2c1 ]
    [ DNSNSRecord :object_type "DNSNSRecord" ]
    [ Website :Website/hostname Hostname ]
    [ Website :Website/primary_key "test_pk" ]
    [ Website :object_type "Website" ]]}}"""

    assert query.format() == expected_query


def test_aliased_query_starting_with_hostname(mocker):
    mocker.patch("octopoes.xtdb.query.uuid4", return_value=UUID("311d6399-4bb4-4830-b077-661cc3f4f2c1"))
    path = Path.parse(
        "Hostname.<hostname[is DNSMXRecord].mail_hostname.<hostname[is DNSARecord].address.<address[is IPPort]"
    )
    query = Query.from_path(path)

    expected_query = """{:query {:find [(pull IPPort [*])] :where [
    [ DNSARecord :DNSARecord/address IPAddressV4 ]
    [ DNSARecord :DNSARecord/hostname ?311d6399-4bb4-4830-b077-661cc3f4f2c1 ]
    [ DNSARecord :object_type "DNSARecord" ]
    [ DNSMXRecord :DNSMXRecord/hostname Hostname ]
    [ DNSMXRecord :DNSMXRecord/mail_hostname ?311d6399-4bb4-4830-b077-661cc3f4f2c1 ]
    [ DNSMXRecord :object_type "DNSMXRecord" ]
    [ IPPort :IPPort/address IPAddressV4 ]
    [ IPPort :object_type "IPPort" ]]}}"""
    assert query.format() == expected_query
