import json
from collections.abc import Callable
from functools import cache
from importlib import import_module
from pathlib import Path
from typing import Iterable

import pytest

from boefjes.job_models import NormalizerOutput
from octopoes.models.ooi.network import IPAddressV4, Network

# PLUGINS_PATH = "boefjes/plugins/*"
# NORMALIZERS_PATH = "**/normalize.py"
# TESTS_PATH = "tests/*-input*"
PLUGINS_PATH = Path("boefjes/plugins")
TESTS_INPUTS_PATH = Path("tests/inputs")
TESTS_OUTPUTS_PATH = Path("tests/outputs")

DEFAULT_INPUT_OOI = {
    "object_type": "HostnameHTTPURL",
    "network": "Network|internet",
    "scheme": "https",
    "port": 443,
    "path": "/",
    "netloc": "Hostname|internet|example.com",
}


class MissingPluginException(Exception):
    """Exception class for unit-tests where no plugin was located"""


class NoOutputFileException(Exception):
    """Exception class for unit-tests where no output file was located"""


def get_dummy_data(filename: str) -> bytes:
    return Path(filename).read_bytes()


def _extract_plugin_id_from_path(path: Path, base_path: Path) -> str:
    """Extracts the plugin id from the path to a module"""
    return ".".join(path.relative_to(base_path).parts[:-1])


@cache
def get_run_method(normalizer_id: str, plugins_path: Path = None) -> Callable:
    if plugins_path is None:
        plugins_path = Path()

    normalizer = import_module(plugins_path.joinpath(normalizer_id).as_posix().replace("/", ".") + ".normalize")
    return getattr(normalizer, "run")


def get_normalizer_modules(plugins_path: Path) -> list[Path]:
    """Finds all normalizer modules in the plugins directory"""
    normalizer_modules = []

    for plugin in plugins_path.rglob("normalize.py"):
        if plugin.is_file():
            normalizer_modules.append(plugin)

    return normalizer_modules


def get_test_input_files(test_inputs_path: Path) -> list[Path]:
    """Finds all files with the test-input filename and the related output files"""
    test_inputs = []
    for input_filename in Path(test_inputs_path).rglob("*.raw"):
        if input_filename.is_file():
            test_inputs.append(input_filename)

    return test_inputs


def get_test_output_files(test_outputs_path: Path) -> list[Path]:
    """Finds all files with the test-input filename and the related output files"""
    test_outputs = []
    for output_filename in Path(test_outputs_path).rglob("test-*.json"):
        if output_filename.is_file():
            test_outputs.append(output_filename)

    return test_outputs


# Maps plugin IDs to run methods
def _map_plugin_id_to_normalizer_function(plugins_path: Path) -> dict[str, Callable]:
    """Maps plugin IDs to their run methods"""
    plugins = {}

    # Populate the plugin_map with the run methods
    for module_path in get_normalizer_modules(plugins_path):
        plugin_id = _extract_plugin_id_from_path(module_path, plugins_path)
        plugins[plugin_id] = get_run_method(plugin_id, plugins_path)

    return plugins


# def get_test_files(pluginspath, normalizerspath, testspath):
#     """Finds all files with the test-input filename and the related output files"""
#     tests = []
#
#     for plugin in Path().glob(pluginspath):
#         for normalizer in Path(plugin).glob(normalizerspath):
#             for input_filename in Path(normalizer.parent).glob(testspath):
#                 input_data = get_dummy_data(input_filename)
#                 output_filename = str(input_filename).replace("input", "output")
#
#                 if Path(output_filename).with_suffix(".json").is_file():
#                     output_data = json.loads(get_dummy_data(output_filename))
#                 elif Path(output_filename).with_suffix(".txt").is_file():
#                     output_data = get_dummy_data(Path(output_filename).with_suffix(".txt")).decode('UTF-8')
#                 elif Path(output_filename).with_suffix(".py").is_file():
#                     output_module = import_module(str(Path(output_filename).with_suffix("")).replace("/", "."))
#                     output_data = getattr(output_module, "output")
#                 else:
#                     raise NoOutputFileException(f"no output file located for {input_filename}")
#
#                 ooi_data_filename = str(input_filename).replace("input", "ooi")
#                 if Path(ooi_data_filename).is_file():
#                     input_ooi_data = json.loads(get_dummy_data(ooi_data_filename))
#                 else:
#                     input_ooi_data = DEFAULT_INPUT_OOI
#                 tests.append((get_run_method(normalizer), input_data, output_data, input_ooi_data))
#     return tests


# todo: add input_ooi_data to the test files
def get_test_files(plugins_path: Path, inputs_path: Path, outputs_path: Path) -> list[
    tuple[str, Path, Path, Path | None, str]]:
    """Finds all files with the test-input filename and the related output files"""
    tests = []

    # todo: perhaps we don't need a plugins map?
    plugins_map: dict[str, Callable] = {}  # Maps plugin IDs to run methods
    inputs_map: dict[tuple[str, str], Path] = {}  # Maps (plugin_id, input name) to input files
    inputs_object_map: dict[tuple[str, str], Path] = {}  # Maps (plugin_id, input name) to input object
    outputs_map: dict[tuple[str, str, str], Path] = {}  # Maps (plugin_id, input name, strategy) to output files

    # Populate inputs_map
    for input_file in get_test_input_files(inputs_path):
        # extract the plugin id from the input file path
        plugin_id = _extract_plugin_id_from_path(input_file, inputs_path)
        # extract name of the input file
        input_file_name = input_file.stem

        inputs_map[(plugin_id, input_file_name)] = input_file

        if (input_object_file := input_file.with_suffix(".json")).is_file():
            inputs_object_map[(plugin_id, input_file_name)] = input_object_file

    # Populate outputs_map
    for output_file in get_test_output_files(outputs_path):
        # extract the plugin id from the output file path
        plugin_id = _extract_plugin_id_from_path(output_file, outputs_path)

        # derive the strategy and input file name from the output file name format ('test-<strategy>-<input file>.json')
        match output_file.stem.split("-"):
            case ["test", strategy, *input_file_name]:
                pass
            case _:
                raise ValueError(f"Invalid output file name format: {output_file.stem}")

        outputs_map[(plugin_id, "-".join(input_file_name), strategy)] = output_file

    # Combine inputs and outputs into tests
    for (plugin_id, input_name), input_file in inputs_map.items():
        for (out_plugin_id, out_name, strategy), output_file in outputs_map.items():
            if plugin_id == out_plugin_id and input_name == out_name:
                input_object_file = inputs_object_map.get((plugin_id, input_name), None)
                tests.append((plugin_id, input_file, output_file, input_object_file, strategy))

    return tests


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    test_files = get_test_files(PLUGINS_PATH, TESTS_INPUTS_PATH, TESTS_OUTPUTS_PATH)

    if metafunc.definition.name == "test_input_output":
        # Generate test cases based on the test_data list
        metafunc.parametrize("plugin_id,test_input,expected_output,input_object_file,strategy", test_files)


# def pytest_generate_tests(metafunc):
#     test_files = get_test_files(PLUGINS_PATH, NORMALIZERS_PATH, TESTS_PATH)
#     if metafunc.definition.name == 'test_input_output':
#         # Generate test cases based on the test_data list
#         metafunc.parametrize("method,test_input,expected_output,input_ooi_data", test_files)


# def field_filter(filters, objectlist):
#     """Walks over a list of objects and removes unknown fields by checking the field keys for
#     each object against the filters allow list for that object type."""
#     for ooi in objectlist:
#         if filters[ooi["type"]]:
#             for objectfield in list(ooi.keys()):
#                 if objectfield not in filters[ooi["type"]]:
#                     del ooi[objectfield]
#     return objectlist


def test_input_output(plugin_id, test_input, expected_output, input_object_file, strategy):
    run_method = plugin_map[plugin_id]

    if input_object_file is None:
        input_object = DEFAULT_INPUT_OOI
    else:
        with input_object_file.open("rb") as input_file:
            input_object = json.load(input_file)

    input_data = get_dummy_data(test_input)
    test_output = _serialize_output(run_method(input_object, input_data))

    with expected_output.open("rb") as output_file:
        expected_output_data = json.load(output_file)

    # todo: allow list[dict | str]; str for references/ primary key comparison
    assert isinstance(expected_output_data,
                      list), f"Expected output data to be a list, got {type(expected_output_data)}"

    # todo: fix and generalize (probably better to use a different test method for each strategy)
    # todo: make OOI comparable with dict (using a custom __eq__ method or a wrapped ooi object suitable for comparison)
    if strategy == "matches":
        assert len(test_output) == len(expected_output_data)
        for i, obj in enumerate(test_output):
            _compare_objects(expected_output_data[i], obj)

    elif strategy == "contains":
        missing = []
        for i, obj in enumerate(expected_output_data):
            found = False
            for actual_output_object in test_output:
                try:
                    # Check if the object is in the test output
                    _compare_objects(obj, actual_output_object)
                    found = True
                    break
                except AssertionError:
                    pass

            if not found:
                missing.append(obj)

        if missing:
            pytest.fail(f"Expected objects not found in test output: {missing}")

    else:
        pytest.fail(f"Unknown strategy: {strategy}")

    # if isinstance(expected_output, str):
    #     assert expected_output == str(test_output)
    # else:
    #     results = set(list(test_output))
    #     extra_in_given = results - expected_output  # this expects the yielded objects to be hasheable.
    #     extra_in_expected = expected_output - results
    #     assert not extra_in_given
    #     assert not extra_in_expected


plugin_map: dict[str, Callable[[dict, bytes], Iterable[NormalizerOutput]]] = _map_plugin_id_to_normalizer_function(
    PLUGINS_PATH)


def _serialize_output(objects: Iterable[NormalizerOutput]) -> list[dict]:
    return list(map(lambda x: x.serialize(), objects))


def _compare_objects(expected: dict | str, actual: dict) -> None:
    """Compare two objects and return True if they are equal."""

    if isinstance(expected, str):
        # If expected is a string, compare it with the actual object's primary key
        assert expected == actual["primary_key"], f"Expected {expected}, got {actual['primary_key']}"
    else:
        # Compare the object types
        assert expected["object_type"] == actual[
            "object_type"], f"Expected {expected['object_type']}, got {actual['object_type']}"

        # Compare the object data
        for key in expected.keys():
            assert key in actual, f"Key {key} not found in actual object"
            assert expected[key] == actual[key], f"Expected {expected[key]}, got {actual[key]} for key {key}"
