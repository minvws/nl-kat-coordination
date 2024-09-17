import os

import pytest

from boefjes.models import Boefje, Normalizer, Organisation

pytestmark = pytest.mark.skipif(os.environ.get("CI") != "1", reason="Needs a CI database.")


def test_get_local_plugin(test_client, organisation):
    response = test_client.get(f"/v1/organisations/{organisation.id}/plugins/dns-records")
    assert response.status_code == 200
    data = response.json()

    assert data["id"] == "dns-records"


def test_filter_plugins(test_client, organisation):
    response = test_client.get(f"/v1/organisations/{organisation.id}/plugins/")
    assert len(response.json()) == 99
    response = test_client.get(f"/v1/organisations/{organisation.id}/plugins?plugin_type=boefje")
    assert len(response.json()) == 44

    response = test_client.get(f"/v1/organisations/{organisation.id}/plugins?limit=10")
    assert len(response.json()) == 10

    response = test_client.get(
        f"/v1/organisations/{organisation.id}/plugins", params={"oci_image": "ghcr.io/minvws/openkat/nmap:latest"}
    )
    assert {x["id"] for x in response.json()} == {"nmap", "nmap-udp"}  # Nmap TCP and UDP

    boefje = Boefje(
        id="test_plugin", name="My test boefje", static=False, oci_image="ghcr.io/minvws/openkat/nmap:latest"
    )
    response = test_client.post(f"/v1/organisations/{organisation.id}/plugins", content=boefje.json())
    assert response.status_code == 201

    response = test_client.get(
        f"/v1/organisations/{organisation.id}/plugins", params={"oci_image": "ghcr.io/minvws/openkat/nmap:latest"}
    )
    assert {x["id"] for x in response.json()} == {"nmap", "nmap-udp", "test_plugin"}  # Nmap TCP and UDP


def test_cannot_add_plugin_reserved_id(test_client, organisation):
    boefje = Boefje(id="dns-records", name="My test boefje", static=False)
    response = test_client.post(f"/v1/organisations/{organisation.id}/plugins", content=boefje.json())
    assert response.status_code == 400
    assert response.json() == {"message": "Plugin id 'dns-records' is already used"}

    normalizer = Normalizer(id="kat_nmap_normalize", name="My test normalizer")
    response = test_client.post(f"/v1/organisations/{organisation.id}/plugins", content=normalizer.json())
    assert response.status_code == 400
    assert response.json() == {"message": "Plugin id 'kat_nmap_normalize' is already used"}


def test_add_boefje(test_client, organisation):
    boefje = Boefje(id="test_plugin", name="My test boefje", static=False)
    response = test_client.post(f"/v1/organisations/{organisation.id}/plugins", content=boefje.json())
    assert response.status_code == 201

    response = test_client.post(f"/v1/organisations/{organisation.id}/plugins", json={"a": "b"})
    assert response.status_code == 422

    response = test_client.get(f"/v1/organisations/{organisation.id}/plugins/?plugin_type=boefje")
    assert len(response.json()) == 45

    boefje_dict = boefje.dict()
    boefje_dict["consumes"] = list(boefje_dict["consumes"])
    boefje_dict["produces"] = list(boefje_dict["produces"])

    response = test_client.get(f"/v1/organisations/{organisation.id}/plugins/test_plugin")
    assert response.json() == boefje_dict


def test_delete_boefje(test_client, organisation):
    boefje = Boefje(id="test_plugin", name="My test boefje", static=False)
    response = test_client.post(f"/v1/organisations/{organisation.id}/plugins", content=boefje.json())
    assert response.status_code == 201

    response = test_client.delete(f"/v1/organisations/{organisation.id}/boefjes/test_plugin")
    assert response.status_code == 204
    response = test_client.get(f"/v1/organisations/{organisation.id}/plugins/test_plugin")
    assert response.status_code == 404


def test_add_normalizer(test_client, organisation):
    normalizer = Normalizer(id="test_normalizer", name="My test normalizer", static=False)
    response = test_client.post(f"/v1/organisations/{organisation.id}/plugins", content=normalizer.json())
    assert response.status_code == 201

    response = test_client.get(f"/v1/organisations/{organisation.id}/plugins/?plugin_type=normalizer")
    assert len(response.json()) == 56

    response = test_client.get(f"/v1/organisations/{organisation.id}/plugins/test_normalizer")
    assert response.json() == normalizer.dict()


def test_delete_normalizer(test_client, organisation):
    normalizer = Normalizer(id="test_normalizer", name="My test normalizer", static=False)
    response = test_client.post(f"/v1/organisations/{organisation.id}/plugins", content=normalizer.json())
    assert response.status_code == 201

    response = test_client.delete(f"/v1/organisations/{organisation.id}/normalizers/test_normalizer")
    assert response.status_code == 204
    response = test_client.get(f"/v1/organisations/{organisation.id}/plugins/test_normalizer")
    assert response.status_code == 404


def test_update_plugins(test_client, organisation):
    normalizer = Normalizer(id="norm_id", name="My test normalizer")
    boefje = Boefje(id="test_plugin", name="My test boefje", description="123")

    test_client.post(f"/v1/organisations/{organisation.id}/plugins", content=boefje.json())
    test_client.patch(f"/v1/organisations/{organisation.id}/boefjes/{boefje.id}", json={"description": "4"})
    test_client.patch(f"/v1/organisations/{organisation.id}/boefjes/{boefje.id}", json={"scan_level": 3})
    test_client.patch(f"/v1/organisations/{organisation.id}/plugins/{boefje.id}", json={"enabled": True})

    response = test_client.get(f"/v1/organisations/{organisation.id}/plugins/{boefje.id}")
    assert response.json()["description"] == "4"
    assert response.json()["scan_level"] == 3
    assert response.json()["enabled"] is True

    test_client.post(f"/v1/organisations/{organisation.id}/plugins", content=normalizer.json())
    test_client.patch(f"/v1/organisations/{organisation.id}/normalizers/{normalizer.id}", json={"version": "v1.2"})

    response = test_client.get(f"/v1/organisations/{organisation.id}/plugins/{normalizer.id}")
    assert response.json()["version"] == "v1.2"


def test_cannot_create_boefje_with_invalid_schema(test_client, organisation):
    boefje = Boefje(id="test_plugin", name="My test boefje", description="123").model_dump(mode="json")
    boefje["schema"] = {"$schema": 3}

    r = test_client.post(f"/v1/organisations/{organisation.id}/plugins", json=boefje)
    assert r.status_code == 400


def test_update_boefje_schema(test_client, organisation):
    boefje = Boefje(id="test_plugin", name="My test boefje", description="123")
    test_client.post(f"/v1/organisations/{organisation.id}/plugins", content=boefje.json())

    r = test_client.patch(f"/v1/organisations/{organisation.id}/boefjes/{boefje.id}", json={"schema": {"$schema": 3}})
    assert r.status_code == 400

    valid_schema = {
        "title": "Arguments",
        "type": "object",
        "properties": {
            "MY_KEY": {
                "title": "MY_KEY",
                "type": "integer",
            }
        },
        "required": [],
    }
    r = test_client.patch(f"/v1/organisations/{organisation.id}/boefjes/{boefje.id}", json={"schema": valid_schema})
    assert r.status_code == 204

    schema = test_client.get(f"/v1/organisations/{organisation.id}/plugins/{boefje.id}/schema.json").json()
    assert schema == valid_schema

    api_boefje = test_client.get(f"/v1/organisations/{organisation.id}/plugins/{boefje.id}").json()
    assert api_boefje["schema"] == valid_schema

    r = test_client.patch(f"/v1/organisations/{organisation.id}/boefjes/dns-records", json={"schema": valid_schema})
    assert r.status_code == 404


def test_cannot_update_static_plugins(test_client, organisation):
    r = test_client.patch(f"/v1/organisations/{organisation.id}/boefjes/dns-records", json={"id": "4", "version": "s"})
    assert r.status_code == 404
    r = test_client.patch(f"/v1/organisations/{organisation.id}/boefjes/dns-records", json={"name": "Overwrite name"})
    assert r.status_code == 404

    response = test_client.get(f"/v1/organisations/{organisation.id}/plugins/dns-records")
    assert response.json()["name"] == "DNS records"
    assert response.json()["version"] is None
    assert response.json()["id"] == "dns-records"

    test_client.patch(f"/v1/organisations/{organisation.id}/plugins/dns-records", json={"enabled": True})
    response = test_client.get(f"/v1/organisations/{organisation.id}/plugins/dns-records")
    assert response.json()["enabled"] is True

    response = test_client.patch(f"/v1/organisations/{organisation.id}/boefjes/dns-records", json={"version": "v1.2"})
    assert response.status_code == 400

    response = test_client.get(f"/v1/organisations/{organisation.id}/plugins/dns-records")
    assert response.json()["version"] != "v1.2"


def test_basic_settings_api(test_client, organisation):
    plug = "dns-records"

    test_client.put(f"/v1/organisations/{organisation.id}/{plug}/settings", json={"new": "settings", "with integer": 5})
    response = test_client.get(f"/v1/organisations/{organisation.id}/{plug}/settings")
    assert response.json() == {"new": "settings", "with integer": 5}

    test_client.put(f"/v1/organisations/{organisation.id}/{plug}/settings", json={"with integer": 8})
    response = test_client.get(f"/v1/organisations/{organisation.id}/{plug}/settings")
    assert response.json() == {"with integer": 8}

    test_client.delete(f"/v1/organisations/{organisation.id}/{plug}/settings")
    response = test_client.get(f"/v1/organisations/{organisation.id}/{plug}/settings")
    assert response.json() == {}


def test_clone_settings(test_client, organisation):
    plug = "dns-records"

    # Set a setting on the first organisation and enable dns-records
    test_client.put(
        f"/v1/organisations/{organisation.id}/{plug}/settings",
        json={"test_key": "test value", "test_key_2": "test value 2"},
    )
    test_client.patch(f"/v1/organisations/{organisation.id}/plugins/{plug}", json={"enabled": True})

    assert test_client.get(f"/v1/organisations/{organisation.id}/{plug}/settings").json() == {
        "test_key": "test value",
        "test_key_2": "test value 2",
    }
    assert test_client.get(f"/v1/organisations/{organisation.id}/plugins/{plug}").json()["enabled"] is True

    # Add the second organisation
    new_org_id = "org2"
    org2 = Organisation(id=new_org_id, name="Second test Organisation")
    test_client.post("/v1/organisations/", content=org2.json())
    test_client.put(f"/v1/organisations/{new_org_id}/{plug}/settings", json={"test_key": "second value"})

    # Show that the second organisation has no settings and dns-records is not enabled
    assert test_client.get(f"/v1/organisations/{new_org_id}/{plug}/settings").json() == {"test_key": "second value"}
    assert test_client.get(f"/v1/organisations/{new_org_id}/plugins/{plug}").json()["enabled"] is False

    # Enable two boefjes that should get disabled by the cloning
    test_client.patch(f"/v1/organisations/{new_org_id}/plugins/nmap", json={"enabled": True})
    assert test_client.get(f"/v1/organisations/{new_org_id}/plugins/nmap").json()["enabled"] is True

    # Call the clone endpoint
    test_client.post(f"/v1/organisations/{organisation.id}/settings/clone/{new_org_id}")

    # Verify that all settings are copied
    response = test_client.get(f"/v1/organisations/{new_org_id}/{plug}/settings")
    assert response.json() == {"test_key": "test value", "test_key_2": "test value 2"}

    # And that the enabled boefje from the original organisation got enabled
    response = test_client.get(f"/v1/organisations/{new_org_id}/plugins/{plug}")
    assert response.json()["enabled"] is True

    # And the originally enabled boefje got disabled
    response = test_client.get(f"/v1/organisations/{new_org_id}/plugins/nmap")
    assert response.json()["enabled"] is False
