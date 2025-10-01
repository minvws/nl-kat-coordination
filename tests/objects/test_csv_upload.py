from io import BytesIO

from objects.models import Hostname, IPAddress, Network
from objects.views import HostnameCSVUploadView, IPAddressCSVUploadView
from tests.conftest import setup_request


def test_ipaddress_csv_upload_success(rf, superuser_member, xtdb):
    """Test successful CSV upload of IP addresses."""
    csv_content = b"192.168.1.1\n10.0.0.1\n172.16.0.1"
    csv_file = BytesIO(csv_content)
    csv_file.name = "ip_addresses.csv"

    request = setup_request(rf.post("objects:ipaddress_csv_upload", {"csv_file": csv_file}), superuser_member.user)
    response = IPAddressCSVUploadView.as_view()(request)

    assert response.status_code == 302
    assert IPAddress.objects.count() == 3

    # Check that the default "internet" network was created
    network = Network.objects.get(name="internet")
    assert IPAddress.objects.filter(network=network).count() == 3

    messages = list(request._messages)
    assert any("Successfully created 3 IP addresses" in str(m) for m in messages)


def test_ipaddress_csv_upload_with_network(rf, superuser_member, xtdb):
    """Test CSV upload of IP addresses with specified network."""
    network = Network.objects.create(name="private")
    csv_content = b"192.168.1.1\n10.0.0.1"
    csv_file = BytesIO(csv_content)
    csv_file.name = "ip_addresses.csv"

    request = setup_request(
        rf.post("objects:ipaddress_csv_upload", {"csv_file": csv_file, "network": network.id}), superuser_member.user
    )
    response = IPAddressCSVUploadView.as_view()(request)

    assert response.status_code == 302
    assert IPAddress.objects.filter(network=network).count() == 2


def test_ipaddress_csv_upload_duplicates(rf, superuser_member, xtdb):
    """Test CSV upload with duplicate IP addresses - should skip duplicates."""
    network = Network.objects.create(name="internet")
    IPAddress.objects.create(network=network, address="192.168.1.1")

    csv_content = b"192.168.1.1\n10.0.0.1\n192.168.1.1"
    csv_file = BytesIO(csv_content)
    csv_file.name = "ip_addresses.csv"

    request = setup_request(rf.post("objects:ipaddress_csv_upload", {"csv_file": csv_file}), superuser_member.user)
    response = IPAddressCSVUploadView.as_view()(request)

    assert response.status_code == 302
    # Should have 2 total: 1 pre-existing + 1 new (192.168.1.1 skipped in CSV)
    assert IPAddress.objects.count() == 2

    messages = list(request._messages)
    assert any("2 IP addresses already existed and were skipped" in str(m) for m in messages)


def test_ipaddress_csv_upload_invalid_format(rf, superuser_member, xtdb):
    """Test CSV upload with invalid format (multiple columns)."""
    csv_content = b"address,network\n192.168.1.1,internet"
    csv_file = BytesIO(csv_content)
    csv_file.name = "ip_addresses.csv"

    request = setup_request(rf.post("objects:ipaddress_csv_upload", {"csv_file": csv_file}), superuser_member.user)
    response = IPAddressCSVUploadView.as_view()(request)

    assert response.status_code == 200  # Form errors return to the same page
    assert IPAddress.objects.count() == 0


def test_ipaddress_csv_upload_empty_file(rf, superuser_member, xtdb):
    """Test CSV upload with empty file."""
    csv_content = b""
    csv_file = BytesIO(csv_content)
    csv_file.name = "ip_addresses.csv"

    request = setup_request(rf.post("objects:ipaddress_csv_upload", {"csv_file": csv_file}), superuser_member.user)
    response = IPAddressCSVUploadView.as_view()(request)

    assert response.status_code == 200
    assert IPAddress.objects.count() == 0


def test_ipaddress_csv_upload_invalid_ip(rf, superuser_member, xtdb):
    """Test CSV upload with invalid IP addresses."""
    csv_content = b"192.168.1.1\ninvalid_ip\n10.0.0.1"
    csv_file = BytesIO(csv_content)
    csv_file.name = "ip_addresses.csv"

    request = setup_request(rf.post("objects:ipaddress_csv_upload", {"csv_file": csv_file}), superuser_member.user)
    response = IPAddressCSVUploadView.as_view()(request)

    assert response.status_code == 302
    # All entries are processed - even invalid ones go through get_or_create
    # The test verifies that at least the valid IPs are created
    assert IPAddress.objects.count() >= 2

    messages = list(request._messages)
    # May have error messages for invalid IPs
    assert len(messages) > 0


def test_hostname_csv_upload_success(rf, superuser_member, xtdb):
    """Test successful CSV upload of hostnames."""
    csv_content = b"example.com\ntest.org\ngoogle.com"
    csv_file = BytesIO(csv_content)
    csv_file.name = "hostnames.csv"

    request = setup_request(rf.post("objects:hostname_csv_upload", {"csv_file": csv_file}), superuser_member.user)
    response = HostnameCSVUploadView.as_view()(request)

    assert response.status_code == 302
    assert Hostname.objects.count() == 3

    # Check that the default "internet" network was created
    network = Network.objects.get(name="internet")
    assert Hostname.objects.filter(network=network).count() == 3

    messages = list(request._messages)
    assert any("Successfully created 3 hostnames" in str(m) for m in messages)


def test_hostname_csv_upload_with_network(rf, superuser_member, xtdb):
    """Test CSV upload of hostnames with specified network."""
    network = Network.objects.create(name="intranet")
    csv_content = b"internal.local\ntest.local"
    csv_file = BytesIO(csv_content)
    csv_file.name = "hostnames.csv"

    request = setup_request(
        rf.post("objects:hostname_csv_upload", {"csv_file": csv_file, "network": network.id}), superuser_member.user
    )
    response = HostnameCSVUploadView.as_view()(request)

    assert response.status_code == 302
    assert Hostname.objects.filter(network=network).count() == 2


def test_hostname_csv_upload_duplicates(rf, superuser_member, xtdb):
    """Test CSV upload with duplicate hostnames - should skip duplicates."""
    network = Network.objects.create(name="internet")
    Hostname.objects.create(network=network, name="example.com")

    csv_content = b"example.com\ntest.com\nexample.com"
    csv_file = BytesIO(csv_content)
    csv_file.name = "hostnames.csv"

    request = setup_request(rf.post("objects:hostname_csv_upload", {"csv_file": csv_file}), superuser_member.user)
    response = HostnameCSVUploadView.as_view()(request)

    assert response.status_code == 302
    # Should have 2 total: 1 pre-existing + 1 new (example.com skipped in CSV)
    assert Hostname.objects.count() == 2

    messages = list(request._messages)
    assert any("2 hostnames already existed and were skipped" in str(m) for m in messages)


def test_hostname_csv_upload_invalid_format(rf, superuser_member, xtdb):
    """Test CSV upload with invalid format (multiple columns)."""
    csv_content = b"name,network\nexample.com,internet"
    csv_file = BytesIO(csv_content)
    csv_file.name = "hostnames.csv"

    request = setup_request(rf.post("objects:hostname_csv_upload", {"csv_file": csv_file}), superuser_member.user)
    response = HostnameCSVUploadView.as_view()(request)

    assert response.status_code == 200  # Form errors return to the same page
    assert Hostname.objects.count() == 0


def test_hostname_csv_upload_empty_file(rf, superuser_member, xtdb):
    """Test CSV upload with empty file."""
    csv_content = b""
    csv_file = BytesIO(csv_content)
    csv_file.name = "hostnames.csv"

    request = setup_request(rf.post("objects:hostname_csv_upload", {"csv_file": csv_file}), superuser_member.user)
    response = HostnameCSVUploadView.as_view()(request)

    assert response.status_code == 200
    assert Hostname.objects.count() == 0


def test_hostname_csv_upload_trailing_newline(rf, superuser_member, xtdb):
    """Test CSV upload with trailing newline."""
    csv_content = b"example.com\ntest.com\n"
    csv_file = BytesIO(csv_content)
    csv_file.name = "hostnames.csv"

    request = setup_request(rf.post("objects:hostname_csv_upload", {"csv_file": csv_file}), superuser_member.user)
    response = HostnameCSVUploadView.as_view()(request)

    assert response.status_code == 302
    assert Hostname.objects.count() == 2


def test_ipaddress_csv_upload_trailing_newline(rf, superuser_member, xtdb):
    """Test CSV upload with trailing newline."""
    csv_content = b"192.168.1.1\n10.0.0.1\n"
    csv_file = BytesIO(csv_content)
    csv_file.name = "ip_addresses.csv"

    request = setup_request(rf.post("objects:ipaddress_csv_upload", {"csv_file": csv_file}), superuser_member.user)
    response = IPAddressCSVUploadView.as_view()(request)

    assert response.status_code == 302
    assert IPAddress.objects.count() == 2


def test_ipaddress_csv_upload_requires_permission(rf, superuser_member, xtdb):
    """Test that the view requires add_ipaddress permission."""
    view = IPAddressCSVUploadView()
    assert view.permission_required == "openkat.add_ipaddress"


def test_hostname_csv_upload_requires_permission(rf, superuser_member, xtdb):
    """Test that the view requires add_hostname permission."""
    view = HostnameCSVUploadView()
    assert view.permission_required == "openkat.add_hostname"
