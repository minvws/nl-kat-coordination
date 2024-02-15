from reports.report_types.rpki_report.report import RPKIReport


def test_rpki_report_no_ip(mock_octopoes_api_connector, valid_time, hostname):
    mock_octopoes_api_connector.oois = {
        hostname.reference: hostname,
    }
    mock_octopoes_api_connector.queries = {
        "Hostname.<hostname[is ResolvedHostname].address": {
            hostname.reference: [],
        },
    }

    report = RPKIReport(mock_octopoes_api_connector)

    data = report.generate_data(str(hostname.reference), valid_time)

    assert data["rpki_ips"] == {}
    assert all(
        v == 0
        for v in [
            data["number_of_available"],
            data["number_of_compliant"],
            data["number_of_valid"],
            data["number_of_ips"],
        ]
    )


def test_rpki_ip_valid(mock_octopoes_api_connector, valid_time, hostname, ipaddressv4, service):
    mock_octopoes_api_connector.oois = {
        ipaddressv4.reference: ipaddressv4,
    }

    mock_octopoes_api_connector.queries = {
        "IPAddress.<ooi[is Finding].finding_type": {
            ipaddressv4.reference: [],
        },
    }

    report = RPKIReport(mock_octopoes_api_connector)

    data = report.generate_data(str(ipaddressv4.reference), valid_time)

    assert all(
        v == 1
        for v in [
            data["number_of_available"],
            data["number_of_compliant"],
            data["number_of_valid"],
            data["number_of_ips"],
        ]
    )

    assert data["rpki_ips"][ipaddressv4.reference] == {"exists": True, "valid": True}


def test_rpki_hostname_with_ip_valid(mock_octopoes_api_connector, valid_time, hostname, ipaddressv4, service):
    mock_octopoes_api_connector.oois = {
        hostname.reference: hostname,
    }

    mock_octopoes_api_connector.queries = {
        "Hostname.<hostname[is ResolvedHostname].address": {
            hostname.reference: [ipaddressv4],
        },
        "IPAddress.<ooi[is Finding].finding_type": {
            ipaddressv4.reference: [],
        },
    }

    report = RPKIReport(mock_octopoes_api_connector)

    data = report.generate_data(str(hostname.reference), valid_time)

    assert all(
        v == 1
        for v in [
            data["number_of_available"],
            data["number_of_compliant"],
            data["number_of_valid"],
            data["number_of_ips"],
        ]
    )

    assert data["rpki_ips"][ipaddressv4.reference] == {"exists": True, "valid": True}


def test_rpki_hostname_with_two_ips_invalid(
    mock_octopoes_api_connector,
    valid_time,
    hostname,
    ipaddressv4,
    ipaddressv6,
    service,
    no_rpki_finding_type,
    expired_rpki_finding_type,
):
    mock_octopoes_api_connector.oois = {
        hostname.reference: hostname,
    }

    mock_octopoes_api_connector.queries = {
        "Hostname.<hostname[is ResolvedHostname].address": {
            hostname.reference: [ipaddressv4, ipaddressv6],
        },
        "IPAddress.<ooi[is Finding].finding_type": {
            ipaddressv4.reference: [no_rpki_finding_type, expired_rpki_finding_type],
            ipaddressv6.reference: [expired_rpki_finding_type],
        },
    }

    report = RPKIReport(mock_octopoes_api_connector)

    data = report.generate_data(str(hostname.reference), valid_time)

    assert data["rpki_ips"][ipaddressv4.reference] == {"exists": False, "valid": False}
    assert data["rpki_ips"][ipaddressv6.reference] == {"exists": True, "valid": False}
    assert data["number_of_available"] == 1
    assert data["number_of_compliant"] == 0
    assert data["number_of_valid"] == 0
    assert data["number_of_ips"] == 2
