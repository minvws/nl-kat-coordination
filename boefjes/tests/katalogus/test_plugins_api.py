def test_list(client):
    res = client.get("/v1/organisations/test/plugins")
    assert res.status_code == 200
    assert {x["id"] for x in res.json()}.issuperset(
        {
            "kat_test",
            "kat_test_2",
            "kat_test_4",
            "kat_test_normalize",
            "kat_test_normalize_2",
        }
    )


def test_list_filter_by_type(client):
    res = client.get("/v1/organisations/test/plugins?plugin_type=boefje")
    assert res.status_code == 200
    assert {x["id"] for x in res.json()}.issuperset(
        {
            "kat_test",
            "kat_test_2",
            "kat_test_4",
        }
    )


def test_list_filter_by_state(client):
    res = client.get("/v1/organisations/test/plugins?state=true")
    assert res.status_code == 200
    assert {x["id"] for x in res.json()}.issuperset(
        {
            "kat_test_normalize",
            "kat_test_normalize_2",
        }
    )
    assert all([x["enabled"] for x in res.json()]) is True


def test_list_filter_by_id(client):
    res = client.get("/v1/organisations/test/plugins?q=norm")
    assert res.status_code == 200
    assert {x["id"] for x in res.json()}.issuperset(
        {
            "kat_test_normalize",
            "kat_test_normalize_2",
        }
    )


def test_list_pagination(client):
    res = client.get("/v1/organisations/test/plugins?offset=2&limit=2&q=kat_")
    assert res.status_code == 200
    assert {x["id"] for x in res.json()}.issuperset(
        {
            "kat_test_4",
            "kat_test_normalize",
        }
    )


def test_list_plugins(client):
    res = client.get("/v1/organisations/test/plugins")
    assert res.status_code == 200
    assert {x["id"] for x in res.json()}.issuperset(
        {"kat_test", "kat_test_2", "kat_test_4", "kat_test_normalize", "kat_test_normalize_2"}
    )


def test_get_plugin(client):
    res = client.get("/v1/organisations/test/plugins/kat_test")
    assert res.status_code == 200
    assert "produces" in res.json()
    assert res.json()["produces"] == ["boefje/kat_test"]


def test_non_existing_plugin(client):
    res = client.get("/v1/organisations/test/plugins/future-plugin")
    assert res.status_code == 404


def test_default_enabled_property_list(client):
    res = client.get("/v1/organisations/test/plugins?plugin_type=boefje")
    assert res.status_code == 200
    assert any([plugin["enabled"] for plugin in res.json()]) is False


def test_patching_enabled_state(client):
    res = client.patch(
        "/v1/organisations/test/plugins/kat_test_normalize",
        json={"enabled": False},
    )
    assert res.status_code == 204

    res = client.get("/v1/organisations/test/plugins")
    assert res.status_code == 200
    assert {plugin["id"]: plugin["enabled"] for plugin in res.json() if "kat_" in plugin["id"]} == {
        "kat_test": False,
        "kat_test_4": False,
        "kat_test_2": False,
        "kat_test_normalize": False,
        "kat_test_normalize_2": True,
    }


def test_patching_enabled_state_non_existing_org(client):
    res = client.patch(
        "/v1/organisations/non-existing-org/plugins/kat_test_normalize",
        json={"enabled": False},
    )

    assert res.status_code == 404

    res = client.get("/v1/organisations/non-existing-org/plugins")
    assert res.status_code == 404
