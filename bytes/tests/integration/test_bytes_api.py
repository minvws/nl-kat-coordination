import uuid

import pytest
import requests
from prometheus_client.parser import text_string_to_metric_families
from requests import HTTPError
from tests.client import BytesAPIClient
from tests.loading import get_boefje_meta, get_normalizer_meta

from bytes.models import MimeType
from bytes.rabbitmq import RabbitMQEventManager
from bytes.repositories.meta_repository import BoefjeMetaFilter, RawDataFilter


def test_login(bytes_api_client: BytesAPIClient) -> None:
    bytes_api_client.login()
    assert "Authorization" in bytes_api_client.headers
    assert "bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" in bytes_api_client.headers["Authorization"]


def test_metrics(bytes_api_client: BytesAPIClient) -> None:
    metrics = bytes_api_client.get_metrics()

    metrics = list(text_string_to_metric_families(metrics.decode()))
    assert len(metrics) == 2
    assert metrics[0].name == "bytes_database_organizations_total"
    assert len(metrics[0].samples) == 1
    assert metrics[1].name == "bytes_database_raw_files_total"
    assert len(metrics[1].samples) == 0

    database_organizations, database_files = metrics

    assert database_organizations.samples[0].value == 0.0

    boefje_meta = get_boefje_meta()
    bytes_api_client.save_boefje_meta(boefje_meta)
    bytes_api_client.save_raw(boefje_meta.id, b"test 123")
    bytes_api_client.save_raw(boefje_meta.id, b"test 12334", ["text/boefje"])

    metrics = bytes_api_client.get_metrics()
    metrics = list(text_string_to_metric_families(metrics.decode()))
    assert len(metrics[0].samples) == 1
    assert len(metrics[1].samples) == 1
    database_organizations, database_files = metrics

    assert database_organizations.samples[0].value == 1.0

    assert database_files.samples[0].labels["organization_id"] == "test"
    assert database_files.samples[0].value == 2.0

    boefje_meta = get_boefje_meta()
    boefje_meta.id = str(uuid.uuid4())
    boefje_meta.organization = "test2"
    bytes_api_client.save_boefje_meta(boefje_meta)
    bytes_api_client.save_raw(boefje_meta.id, b"test 123")

    metrics = bytes_api_client.get_metrics()
    metrics = list(text_string_to_metric_families(metrics.decode()))
    assert len(metrics[0].samples) == 1
    assert len(metrics[1].samples) == 2
    database_organizations, database_files = metrics

    assert database_organizations.samples[0].value == 2.0

    assert len(database_files.samples) == 2
    assert database_files.samples[0].labels["organization_id"] == "test"
    assert database_files.samples[0].value == 2.0
    assert database_files.samples[1].labels["organization_id"] == "test2"
    assert database_files.samples[1].value == 1.0


def test_boefje_meta(bytes_api_client: BytesAPIClient) -> None:
    boefje_meta = get_boefje_meta()
    bytes_api_client.save_boefje_meta(boefje_meta)
    retrieved_boefje_meta = bytes_api_client.get_boefje_meta_by_id(boefje_meta.id)

    assert boefje_meta == retrieved_boefje_meta

    with pytest.raises(HTTPError) as ctx:
        bytes_api_client.save_boefje_meta(boefje_meta)

    assert ctx._excinfo[1].response.json() == {
        "status": "failed",
        "message": "Integrity error: object might already exist",
    }


def test_filtered_boefje_meta(bytes_api_client: BytesAPIClient) -> None:
    boefje_meta = get_boefje_meta()
    bytes_api_client.save_boefje_meta(boefje_meta)

    query_filter = BoefjeMetaFilter(organization=boefje_meta.organization, boefje_id=boefje_meta.boefje.id)
    retrieved_boefje_metas = bytes_api_client.get_boefje_meta(query_filter)

    assert len(retrieved_boefje_metas) == 1
    assert boefje_meta == retrieved_boefje_metas[0]

    second_boefje_meta = get_boefje_meta(str(uuid.uuid4()), input_ooi="Network|internet")
    bytes_api_client.save_boefje_meta(second_boefje_meta)

    query_filter = BoefjeMetaFilter(organization=boefje_meta.organization, boefje_id=boefje_meta.boefje.id, limit=2)
    retrieved_boefje_metas = bytes_api_client.get_boefje_meta(query_filter)
    assert len(retrieved_boefje_metas) == 2
    assert boefje_meta == retrieved_boefje_metas[0]
    assert second_boefje_meta == retrieved_boefje_metas[1]

    query_filter = BoefjeMetaFilter(organization=boefje_meta.organization, input_ooi="Network|internet", limit=2)
    retrieved_boefje_metas = bytes_api_client.get_boefje_meta(query_filter)
    assert len(retrieved_boefje_metas) == 1
    assert second_boefje_meta == retrieved_boefje_metas[0]


def test_normalizer_meta(bytes_api_client: BytesAPIClient, event_manager: RabbitMQEventManager) -> None:
    boefje_meta = get_boefje_meta()
    bytes_api_client.save_boefje_meta(boefje_meta)

    raw = b"test 123"
    raw_id = bytes_api_client.save_raw(boefje_meta.id, raw)
    normalizer_meta = get_normalizer_meta(raw_id)

    bytes_api_client.save_normalizer_meta(normalizer_meta)
    retrieved_normalizer_meta = bytes_api_client.get_normalizer_meta(normalizer_meta.id)

    assert normalizer_meta == retrieved_normalizer_meta

    method, properties, body = event_manager.connection.channel().basic_get("test__normalizer_meta_received")
    event_manager.connection.channel().basic_ack(method.delivery_tag)

    assert normalizer_meta.id in body.decode()


def test_normalizer_meta_pointing_to_raw_id(bytes_api_client: BytesAPIClient) -> None:
    boefje_meta = get_boefje_meta()
    bytes_api_client.save_boefje_meta(boefje_meta)

    raw_id = bytes_api_client.save_raw(boefje_meta.id, b"test 123")
    normalizer_meta = get_normalizer_meta(raw_id)

    bytes_api_client.save_normalizer_meta(normalizer_meta)
    retrieved_normalizer_meta = bytes_api_client.get_normalizer_meta(normalizer_meta.id)

    assert normalizer_meta == retrieved_normalizer_meta


def test_raw(bytes_api_client: BytesAPIClient, event_manager: RabbitMQEventManager) -> None:
    boefje_meta = get_boefje_meta()
    bytes_api_client.save_boefje_meta(boefje_meta)

    raw = b"test 123"
    bytes_api_client.save_raw(boefje_meta.id, raw)

    retrieved_raw = bytes_api_client.get_raw(boefje_meta.id)

    assert retrieved_raw == raw

    method, properties, body = event_manager.connection.channel().basic_get("test__raw_file_received")
    event_manager.connection.channel().basic_ack(method.delivery_tag)

    assert boefje_meta.id in body.decode()


def test_raw_mime(bytes_api_client: BytesAPIClient) -> None:
    boefje_meta = get_boefje_meta(meta_id=str(uuid.uuid4()))
    bytes_api_client.save_boefje_meta(boefje_meta)
    mime_type = "text/kat-test"

    raw = b"test 123456"
    bytes_api_client.save_raw(boefje_meta.id, raw, [mime_type])
    retrieved_raw = bytes_api_client.get_raw(boefje_meta.id, [mime_type])

    assert retrieved_raw == raw

    with pytest.raises(HTTPError):
        bytes_api_client.get_raw(boefje_meta.id, "bad/mime")

    headers = {"content-type": "application/octet-stream"}
    headers.update(bytes_api_client.headers)

    boefje_meta = get_boefje_meta(meta_id=str(uuid.uuid4()))
    bytes_api_client.save_boefje_meta(boefje_meta)

    test_url_without_params = f"{bytes_api_client._session._base_url}/bytes/raw/{boefje_meta.id}"

    second_raw = b"second test 123456"
    create_raw_without_mime_type_response = requests.post(test_url_without_params, data=second_raw, headers=headers)

    assert create_raw_without_mime_type_response.status_code == 200

    get_raw_without_mime_type_response = requests.get(
        test_url_without_params, headers=bytes_api_client.headers, stream=True
    )

    assert get_raw_without_mime_type_response.status_code == 200
    assert get_raw_without_mime_type_response.content == second_raw


def test_raw_mimes(bytes_api_client: BytesAPIClient) -> None:
    boefje_meta = get_boefje_meta(meta_id=str(uuid.uuid4()))
    bytes_api_client.save_boefje_meta(boefje_meta)
    mime_types = ["text/kat-test", "text/html"]
    second_mime_types = ["text/kat-test", "text/status-code"]

    raw = b"test 123456"
    second_raw = b"second test 200"
    bytes_api_client.save_raw(boefje_meta.id, raw, mime_types)
    bytes_api_client.save_raw(boefje_meta.id, second_raw, second_mime_types)

    retrieved_raw = bytes_api_client.get_raw(boefje_meta.id, mime_types)
    assert retrieved_raw == raw

    retrieved_raw = bytes_api_client.get_raw(boefje_meta.id, "text/html")
    assert retrieved_raw == raw

    with pytest.raises(HTTPError):
        bytes_api_client.get_raw(boefje_meta.id, "bad/mime")

    query_filter = RawDataFilter(
        organization=boefje_meta.organization,
        boefje_meta_id=boefje_meta.id,
        mime_types=[MimeType(value="text/kat-test")],
        limit=3,
    )
    retrieved_raws = bytes_api_client.get_raws(query_filter)

    assert len(retrieved_raws) == 2
    assert (
        retrieved_raws[0]["secure_hash"] == "sha512:ce89137e70b5f8433e787293f0c01332c0ca405d355a7080a50630340f7"
        "7bf5227561a01cba83272273513097d91f3bf9a8e8f17416fadfc1575028157cef2df"
    )
    assert (
        retrieved_raws[1]["secure_hash"] == "sha512:0ae68528b2daf4d9fd494ee378b043be8646489dbe1e7d63bbf33560f58"
        "d6c9b5abaa05387644c635f0c8a327a261e1435ad78de0cb30745d8bb05d76ddda612"
    )


def test_cannot_overwrite_raw(bytes_api_client: BytesAPIClient) -> None:
    boefje_meta = get_boefje_meta()
    bytes_api_client.save_boefje_meta(boefje_meta)

    right_raw = b"test 123"
    bytes_api_client.save_raw(boefje_meta.id, right_raw)
    bytes_api_client.save_raw(boefje_meta.id, b"321 test")

    retrieved_raw = bytes_api_client.get_raw(boefje_meta.id)

    assert retrieved_raw == right_raw
