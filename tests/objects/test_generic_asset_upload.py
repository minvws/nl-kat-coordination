from io import BytesIO

from objects.models import Hostname, IPAddress, Network, ScanLevel
from objects.views import GenericAssetCreateView, GenericAssetCSVUploadView, is_valid_ip
from tests.conftest import setup_request


def test_is_valid_ip():
    assert is_valid_ip("192.168.1.1")
    assert is_valid_ip("10.0.0.1")
    assert is_valid_ip("2001:db8::1")
    assert is_valid_ip("::1")
    assert not is_valid_ip("example.com")
    assert not is_valid_ip("test.org")
    assert not is_valid_ip("not-an-ip")


def test_generic_asset_bulk_create_success(rf, superuser_member, xtdb):
    form_data = {"assets": "192.168.1.1\nexample.com\n10.0.0.1\ntest.org"}

    request = setup_request(rf.post("objects:generic_asset_create", form_data), superuser_member.user)
    response = GenericAssetCreateView.as_view()(request)

    assert response.status_code == 302
    assert IPAddress.objects.count() == 2
    assert Hostname.objects.count() == 2

    # Check that the default "internet" network was created
    network = Network.objects.get(name="internet")
    assert IPAddress.objects.filter(network=network).count() == 2
    assert Hostname.objects.filter(network=network).count() == 2


def test_generic_asset_csv_upload_basic(rf, superuser_member, xtdb):
    csv_content = b"192.168.1.1\nexample.com\n10.0.0.1"
    csv_file = BytesIO(csv_content)
    csv_file.name = "assets.csv"

    request = setup_request(rf.post("objects:generic_asset_csv_upload", {"csv_file": csv_file}), superuser_member.user)
    response = GenericAssetCSVUploadView.as_view()(request)

    assert response.status_code == 302
    assert IPAddress.objects.count() == 2
    assert Hostname.objects.count() == 1


def test_generic_asset_csv_upload_with_scan_level(rf, superuser_member, xtdb):
    organization = superuser_member.organization
    org_code = organization.code

    csv_content = f"192.168.1.1,2,{org_code}\nexample.com,3,{org_code}".encode()
    csv_file = BytesIO(csv_content)
    csv_file.name = "assets.csv"

    request = setup_request(rf.post("objects:generic_asset_csv_upload", {"csv_file": csv_file}), superuser_member.user)
    response = GenericAssetCSVUploadView.as_view()(request)

    assert response.status_code == 302
    assert IPAddress.objects.count() == 1
    assert Hostname.objects.count() == 1

    # Check scan levels were set
    ip = IPAddress.objects.first()
    hostname = Hostname.objects.first()

    scan_level_ip = ScanLevel.objects.get(object_id=ip.id, object_type="ipaddress", organization=organization)
    assert scan_level_ip.scan_level == 2
    assert scan_level_ip.declared is True

    scan_level_hostname = ScanLevel.objects.get(
        object_id=hostname.id, object_type="hostname", organization=organization
    )
    assert scan_level_hostname.scan_level == 3
    assert scan_level_hostname.declared is True


def test_generic_asset_csv_upload_ipv6(rf, superuser_member, xtdb):
    """Test CSV upload with IPv6 addresses."""
    csv_content = b"2001:db8::1\n::1\nfe80::1"
    csv_file = BytesIO(csv_content)
    csv_file.name = "assets.csv"

    request = setup_request(rf.post("objects:generic_asset_csv_upload", {"csv_file": csv_file}), superuser_member.user)
    response = GenericAssetCSVUploadView.as_view()(request)

    assert response.status_code == 302
    assert IPAddress.objects.count() == 3


def test_generic_asset_csv_upload_duplicates(rf, superuser_member, xtdb):
    network = Network.objects.create(name="internet")
    IPAddress.objects.create(network=network, address="192.168.1.1")
    Hostname.objects.create(network=network, name="example.com")

    csv_content = b"192.168.1.1\nexample.com\n10.0.0.1\ntest.com"
    csv_file = BytesIO(csv_content)
    csv_file.name = "assets.csv"

    request = setup_request(rf.post("objects:generic_asset_csv_upload", {"csv_file": csv_file}), superuser_member.user)
    response = GenericAssetCSVUploadView.as_view()(request)

    assert response.status_code == 302
    # Should have 2 IPs total: 1 pre-existing + 1 new
    assert IPAddress.objects.count() == 2
    # Should have 2 hostnames total: 1 pre-existing + 1 new
    assert Hostname.objects.count() == 2


def test_generic_asset_csv_upload_optional_columns(rf, superuser_member, xtdb):
    org_code = superuser_member.organization.code
    csv_content = f"192.168.1.1,,\nexample.com,2,\ntest.org,,{org_code}".encode()
    csv_file = BytesIO(csv_content)
    csv_file.name = "assets.csv"

    request = setup_request(rf.post("objects:generic_asset_csv_upload", {"csv_file": csv_file}), superuser_member.user)
    response = GenericAssetCSVUploadView.as_view()(request)

    assert response.status_code == 302
    assert IPAddress.objects.count() == 1
    assert Hostname.objects.count() == 2


def test_generic_asset_csv_upload_requires_permission(rf, superuser_member, xtdb):
    view = GenericAssetCSVUploadView()
    permissions = view.get_permission_required()
    assert "openkat.add_ipaddress" in permissions
    assert "openkat.add_hostname" in permissions
