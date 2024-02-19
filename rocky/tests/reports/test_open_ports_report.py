from reports.report_types.open_ports_report.report import OpenPortsReport


def test_open_ports_report_ip_no_port(mock_octopoes_api_connector, valid_time, service, hostname, ipaddressv4, ip_port):
    mock_octopoes_api_connector.oois = {
        ipaddressv4.reference: ipaddressv4,
    }
    mock_octopoes_api_connector.queries = {
        "IPAddress.<address[is IPPort]": {
            ipaddressv4.reference: [],
        },
        "IPAddress.<address[is ResolvedHostname].hostname": {
            ipaddressv4.reference: [hostname],
        },
    }

    report = OpenPortsReport(mock_octopoes_api_connector)

    data = report.generate_data(str(ipaddressv4.reference), valid_time)

    assert data[ipaddressv4.reference] == {"ports": {}, "hostnames": [hostname.name], "services": {}}


def test_open_ports_report_ip_one_port(
    mock_octopoes_api_connector, valid_time, service, hostname, ipaddressv4, ip_port
):
    mock_octopoes_api_connector.oois = {
        ipaddressv4.reference: ipaddressv4,
    }
    mock_octopoes_api_connector.queries = {
        "IPAddress.<address[is IPPort]": {
            ipaddressv4.reference: [ip_port],
        },
        "IPAddress.<address[is ResolvedHostname].hostname": {
            ipaddressv4.reference: [hostname],
        },
        "IPPort.<ip_port [is IPService].service": {
            ip_port.reference: [service],
        },
    }

    report = OpenPortsReport(mock_octopoes_api_connector)

    data = report.generate_data(str(ipaddressv4.reference), valid_time)

    assert data[ipaddressv4.reference] == {
        "ports": {80: False},
        "hostnames": [hostname.name],
        "services": {80: [service.name]},
    }


def test_open_ports_report_hostname_one_port(
    mock_octopoes_api_connector, valid_time, service, hostname, ipaddressv4, ip_port
):
    mock_octopoes_api_connector.oois = {
        hostname.reference: hostname,
    }
    mock_octopoes_api_connector.queries = {
        "Hostname.<hostname[is ResolvedHostname].address": {
            hostname.reference: [ipaddressv4],
        },
        "IPAddress.<address[is IPPort]": {
            ipaddressv4.reference: [ip_port],
        },
        "IPAddress.<address[is ResolvedHostname].hostname": {
            ipaddressv4.reference: [hostname],
        },
        "IPPort.<ip_port [is IPService].service": {
            ip_port.reference: [service],
        },
    }

    report = OpenPortsReport(mock_octopoes_api_connector)

    data = report.generate_data(str(hostname.reference), valid_time)

    assert data[ipaddressv4.reference] == {
        "ports": {80: False},
        "hostnames": [hostname.name],
        "services": {80: [service.name]},
    }
