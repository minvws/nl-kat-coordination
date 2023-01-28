def test_root(client):
    response = client.get("/")
    assert response.status_code == 302
    assert response.headers["Location"] == "/en/"


def test_404(client):
    response = client.get("/en/does/not/exist/")
    assert response.status_code == 404
