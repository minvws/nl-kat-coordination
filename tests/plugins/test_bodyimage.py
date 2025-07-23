import json

from requests.models import CaseInsensitiveDict, PreparedRequest, Response

from katalogus.boefjes.kat_webpage_analysis.check_images.normalize import run as image_run
from katalogus.boefjes.kat_webpage_analysis.find_images_in_html.normalize import run as body_run
from katalogus.boefjes.kat_webpage_analysis.main import run
from katalogus.boefjes.normalizer_handler import LocalNormalizerHandler
from katalogus.worker.job_models import BoefjeMeta, NormalizerMeta
from tests.conftest import get_dummy_data


def test_website_analysis(mocker):
    do_request_mock = mocker.patch("katalogus.boefjes.kat_webpage_analysis.main.do_request", spec=Response)
    meta = BoefjeMeta.model_validate_json(get_dummy_data("webpage-analysis.json"))

    mock_response = Response()
    mock_response._content = bytes(get_dummy_data("download_body"))
    mock_response.request = mocker.MagicMock(spec=PreparedRequest())
    mock_response.request.url = ""
    mock_response.request.method = "GET"
    mock_response.headers = CaseInsensitiveDict(json.loads(get_dummy_data("download_headers.json")))

    do_request_mock.return_value = mock_response

    output = run(meta.input_ooi_data, meta.boefje.model_dump())

    assert "application/json+har" in output[0][0]
    assert "openkat-http/headers" in output[1][0]
    assert "openkat-http/body" in output[2][0]


def test_website_analysis_for_image(mocker):
    do_request_mock = mocker.patch("katalogus.boefjes.kat_webpage_analysis.main.do_request", spec=Response)
    meta = BoefjeMeta.model_validate_json(get_dummy_data("webpage-analysis.json"))

    mock_response = Response()
    mock_response._content = bytes(get_dummy_data("cat_image"))
    mock_response.request = mocker.MagicMock(spec=PreparedRequest())
    mock_response.request.url = ""
    mock_response.request.method = "GET"
    mock_response.headers = CaseInsensitiveDict(json.loads(get_dummy_data("download_image_headers.json")))

    do_request_mock.return_value = mock_response

    output = run(meta.input_ooi_data, meta.boefje.model_dump())
    assert "image/jpeg" in output[2][0]


def test_body_image_normalizer():
    meta = NormalizerMeta.model_validate_json(get_dummy_data("bodyimage-normalize.json"))
    output = LocalNormalizerHandler._parse_results(
        meta, image_run(meta.raw_data.boefje_meta.input_ooi_data, get_dummy_data("cat_image"))
    )

    assert len(output.observations) == 1
    assert len(output.observations[0].results) == 1
    assert output.observations[0].results[0].dict() == {
        "object_type": "ImageMetadata",
        "primary_key": "ImageMetadata|internet|134.209.85.72|tcp|443|https|internet"
        "|mispo.es|https|internet|mispo.es|443|/",
        "resource": "HTTPResource|internet|134.209.85.72|tcp|443|https|internet|mispo.es|https|internet|mispo.es|443|/",
        "scan_profile": None,
        "user_id": None,
        "image_info": {
            "format": "JPEG",
            "frames": 1,
            "height": 600,
            "is_animated": False,
            "mode": "RGB",
            "size": (600, 600),
            "width": 600,
        },
    }


def test_body_normalizer():
    meta = NormalizerMeta.model_validate_json(get_dummy_data("body-normalize.json"))
    output = LocalNormalizerHandler._parse_results(
        meta, body_run(meta.raw_data.boefje_meta.input_ooi_data, get_dummy_data("download_body"))
    )
    assert len(output.observations[0].results) == 4

    output_dicts = sorted([o.model_dump() for o in output.observations[0].results], key=lambda x: x["primary_key"])

    assert output_dicts[0]["primary_key"] == "URL|internet|http://placekitten.com/600/600"
    assert output_dicts[1]["primary_key"] == "URL|internet|http://placekitten.com/600/600.webp"
    assert output_dicts[2]["primary_key"] == "URL|internet|https://mispo.es/600/600"
    assert output_dicts[3]["primary_key"] == "URL|internet|https://mispo.es/600/600.webp"
