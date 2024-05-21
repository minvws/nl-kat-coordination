import json
from importlib import import_module
from pathlib import Path

PLUGINS_PATH = "boefjes/plugins/*"
NORMALIZER_PATH = "**/normalize.py"
TESTS_PATH = "tests/*test-input*"
DEFAULT_INPUT_OOI = {
    "object_type": "HostnameHTTPURL",
    "network": "Network|internet",
    "scheme": "https",
    "port": 443,
    "path": "/",
    "netloc": "Hostname|internet|example.com",
}


class NoOutputFileException(Exception):
    """Exception class for unit-tests where no output file was located"""


def get_dummy_data(filename: str) -> bytes:
    return Path(filename).read_bytes()


def get_run_method(normalizer: str):
    normalizer = import_module(str(Path(normalizer).with_suffix("")).replace("/", "."))
    return getattr(output_module, "run")


def get_test_files(pluginspath, normalizerpath, testpath):
    """Finds all files with the test-input filename and the related output files"""
    tests = []

    for plugin in Path().glob(pluginspath):
        for normalizer in Path(plugin).glob(normalizerpath):
            for input_filename in Path(normalizer.parent).glob(testpath):
                input_data = get_dummy_data(input_filename)
                output_filename = str(input_filename).replace("input", "output")

                if Path(output_filename).with_suffix(".json").is_file():
                    output_data = json.loads(get_dummy_data(output_filename))
                elif Path(output_filename).with_suffix(".py").is_file():
                    output_module = import_module(str(Path(output_filename).with_suffix("")).replace("/", "."))
                    output_data = getattr(output_module, "output")
                else:
                    raise NoOutputFileException(f"no output file located for {input_filename}")

                ooi_data_filename = input_filename.replace("input", "ooi")
                if Path(ooi_data_filename).is_file():
                    input_ooi_data = json.loads(get_dummy_data(ooi_data_filename))
                else:
                    input_ooi_data = DEFAULT_INPUT_OOI
                tests.append((get_run_method(normalizer), input_data, output_data, input_ooi_data))
        return tests


def run_normalizer(input_ooi, inputdata):
    return list(run(input_ooi, inputdata))


def pytest_generate_tests(metafunc):
    test_files = get_test_files(PLUGINS_PATH, NORMALIZER_PATH, TESTS_PATH)
    if "test_input" in metafunc.fixturenames:
        # Generate test cases based on the test_data list
        metafunc.parametrize("method,test_input,expected_output,input_ooi_data", test_files)


def field_filter(filters, objectlist):
    """Walks over a list of objects and removes unknown fields by checking the field keys for
    each object against the filters allow list for that object type."""
    for ooi in objectlist:
        if filters[ooi["type"]]:
            for objectfield in list(ooi.keys()):
                if objectfield not in filters[ooi["type"]]:
                    del ooi[objectfield]
    return objectlist


def test_input_output(method, test_input, expected_output, input_ooi_data):
    results = set(run_normalizer(method, input_ooi_data, test_input))
    extra_in_given = results - expected_output  # this expects the yielded objects to be hasheable.
    extra_in_expected = expected_output - results
    assert not extra_in_given
    assert not extra_in_expected
