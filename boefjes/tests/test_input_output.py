import glob
from pathlib import Path
from unittest import TestCase

from pydantic import parse_obj_as

from boefjes.job_handler import serialize_ooi
from boefjes.plugins.kat_leakix.normalize import run
from octopoes.models.types import OOIType
from tests.loading import get_boefje_meta,  get_normalizer_meta

TESTS_PATH = "boefjes/plugins/*/tests/normalizer/*test-input*"

def get_dummy_data(filename: str) -> bytes:
    return Path(filename).read_bytes()

def get_test_files(testpath):
    """Finds all files with the test-input filename and the related output files"""
    tests = []
    for inputfile in glob.glob(testpath):
        inputdata = get_dummy_data(inputfile)
        outputdata = get_dummy_data(inputfile.replace("input", "output"))
        tests.append((inputdata, outputdata))
    return tests


def create_boefje_meta():
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
    boefje_meta = get_boefje_meta(input_ooi=input_ooi.reference)
    boefje_meta.arguments["input"] = serialize_ooi(input_ooi)
    return boefje_meta


def run_normalizer(boefje_meta, inputdata):
    return [x for x in run(get_normalizer_meta(boefje_meta), inputdata)]


def pytest_generate_tests(metafunc):
    test_files = get_test_files(TESTS_PATH)
    if "test_input" in metafunc.fixturenames:
        # Generate test cases based on the test_data list
        metafunc.parametrize("test_input,expected_output", test_files)


def test_input_output(test_input, expected_output):
    result = run_normalizer(create_boefje_meta(), test_input)
    assert str(result) == expected_output.decode().strip()
