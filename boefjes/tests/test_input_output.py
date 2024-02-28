import glob
import json
import os
from pathlib import Path

from pydantic import parse_obj_as

from boefjes.job_handler import serialize_ooi
from boefjes.plugins.kat_leakix.normalize import run
from octopoes.models.types import OOIType
from tests.loading import get_boefje_meta, get_normalizer_meta

TESTS_PATH = "boefjes/plugins/*/tests/normalizer/*test-input*"


def get_dummy_data(filename: str) -> bytes:
    return Path(filename).read_bytes()


def get_test_files(testpath):
    """Finds all files with the test-input filename and the related output files"""
    tests = []
    for input_filename in glob.glob(testpath):
        input_data = get_dummy_data(input_filename)
        output_data = json.loads(get_dummy_data(input_filename.replace("input", "output")))
        ooi_data_filename = input_filename.replace("input", "ooi")
        if os.path.isfile(ooi_data_filename):
            input_ooi_data = json.loads(get_dummy_data(ooi_data_filename))
        else:
            input_ooi_data = None
        tests.append((input_data, output_data, input_ooi_data))
    return tests


def create_boefje_meta(input_ooi = None):
    if not input_ooi:
        input_ooi = {
            "object_type": "HostnameHTTPURL",
            "network": "Network|internet",
            "scheme": "https",
            "port": 443,
            "path": "/",
            "netloc": "Hostname|internet|example.com",
        }
    input_ooi_object = parse_obj_as(
        OOIType,
        input_ooi,
    )
    boefje_meta = get_boefje_meta(input_ooi=input_ooi_object.reference)
    boefje_meta.arguments["input"] = serialize_ooi(input_ooi_object)
    return boefje_meta


def run_normalizer(boefje_meta, inputdata):
    return [x for x in run(get_normalizer_meta(boefje_meta), inputdata)]


def pytest_generate_tests(metafunc):
    test_files = get_test_files(TESTS_PATH)
    if "test_input" in metafunc.fixturenames:
        # Generate test cases based on the test_data list
        metafunc.parametrize("test_input,expected_output,input_ooi_data", test_files)


def field_filter(filter, objects):
    """Walks over a list of objects and removes unknown fields by checking the field keys for 
    each object agains the filters allow list for that object type."""
    for object in objects:
        if filter[object['type']]:
            for objectfield in list(object.keys()):
                if objectfield not in filter[object['type']]:
                    del(object[objectfield])
    return objects


def test_input_output(test_input, expected_output, input_ooi_data):
    results = set(run_normalizer(create_boefje_meta(input_ooi_data), test_input))
    extra_in_given = results - expected_output # this expects the yielded objects to be hasheable.
    extra_in_expected = expected_output - results
    assert not extra_in_given
    assert not extra_in_expected
