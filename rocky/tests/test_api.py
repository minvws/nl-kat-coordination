from account.models import AuthToken


# Regression test for https://github.com/minvws/nl-kat-coordination/issues/2872
def test_api_2fa_enabled(client, settings, admin_user):
    settings.TWOFACTOR_ENABLED = True

    token_object = AuthToken(name="Test", user=admin_user)
    token = token_object.generate_new_token()
    token_object.save()

    response = client.get("/api/v1/organization/", headers={"Authorization": f"Token {token}"})
    assert response.status_code == 200
