import datetime
from io import BytesIO

from files.models import File
from files.views import FileCreateView
from tests.conftest import setup_request


def test_enable_plugins(rf, superuser_member):
    example_file = BytesIO(b"{}")
    example_file.name = "testname.json"

    request = setup_request(
        rf.post(
            "add_file",
            {"type": "json", "file": example_file},
        ),
        superuser_member.user,
    )
    response = FileCreateView.as_view()(request)

    assert response.status_code == 302
    assert response.headers["Location"] == "/en/files/"
    file = File.objects.first()

    assert file.type == "json"
    assert file.type in file.file.name
    assert example_file.name in file.file.name
    assert str(datetime.datetime.today().date()) in file.file.name
