import json


def test_list(client):
    res = client.get("/v1/organisations")
    assert res.status_code == 200


def test_get_organisation(client):
    res = client.get("/v1/organisations/test")
    assert res.status_code == 200


def test_non_existing_organisation(client):
    res = client.get("/v1/organisations/future-organisation")
    assert res.status_code == 404
    assert "unknown organisation" in res.text.lower()


def test_add_organisation(client):
    res = client.post("/v1/organisations/", content=json.dumps({"id": "new", "name": "New"}))
    assert res.status_code == 201

    res = client.get("/v1/organisations")
    assert res.status_code == 200
    assert len(res.json()) == 2


def test_delete_organisation(client):
    res = client.delete("/v1/organisations/test")
    assert res.status_code == 200

    res = client.get("/v1/organisations")
    assert res.status_code == 200
    assert len(res.json()) == 0
