import json


def test_bulk_create_tasks(drf_client, xtdb):
    n = 300
    tasks = [{"type": f"test{i}"} for i in range(n)]
    drf_client.post("/api/v1/task/", data=json.dumps(tasks), content_type="application/json").json()
    assert drf_client.get("/api/v1/task/").json()["count"] == n
