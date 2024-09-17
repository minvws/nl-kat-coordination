from pydantic import parse_obj_as

from boefjes.plugins.kat_leakix.normalize import run
from octopoes.models.types import OOIType
from tests.loading import get_dummy_data


def test_output():
    input_ooi = parse_obj_as(
        OOIType,
        {
            "object_type": "HostnameHTTPURL",
            "network": "Network|internet",
            "scheme": "https",
            "port": 443,
            "path": "/",
            "netloc": "Hostname|internet|example.com",
        },
    )

    output = [x for x in run(input_ooi.serialize(), get_dummy_data("raw/leakix-example.com.json"))]

    assert len(output) == 170
    assert str(output) == get_dummy_data("raw/leakix-example.com-output.txt").decode().strip()
