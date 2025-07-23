from pydantic import TypeAdapter

from katalogus.boefjes.kat_leakix.normalize import run
from octopoes.models.types import OOIType
from tests.conftest import get_dummy_data


def test_output():
    input_ooi = TypeAdapter(OOIType).validate_python(
        {
            "object_type": "HostnameHTTPURL",
            "network": "Network|internet",
            "scheme": "https",
            "port": 443,
            "path": "/",
            "netloc": "Hostname|internet|example.com",
        }
    )

    output = [x for x in run(input_ooi.serialize(), get_dummy_data("raw/leakix-example.com.json"))]

    assert len(output) == 170
    assert str(output) == get_dummy_data("raw/leakix-example.com-output.txt").decode().strip()
