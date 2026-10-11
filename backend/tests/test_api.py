def test_health(client):
    assert client.get("/health").json() == {"status": "UP"}


def test_ready_checks_db(client):
    assert client.get("/ready").json() == {"status": "READY"}


def test_create_and_get(client):
    r = client.post("/api/incidents", json={"title": "Checkout 500s", "service": "checkout", "severity": "SEV1"})
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "OPEN" and body["owner"] == "on-call"
    assert client.get(f"/api/incidents/{body['id']}").json()["title"] == "Checkout 500s"


def test_rejects_bad_severity(client):
    assert client.post("/api/incidents", json={"title": "x", "severity": "SEV9"}).status_code == 422


def test_update_and_stats(client):
    a = client.post("/api/incidents", json={"title": "DB slow", "severity": "SEV1"}).json()
    client.post("/api/incidents", json={"title": "Typo on page", "severity": "SEV3"})
    r = client.put(f"/api/incidents/{a['id']}", json={"status": "INVESTIGATING"})
    assert r.json()["status"] == "INVESTIGATING"
    assert client.get("/api/incidents/stats").json() == {
        "total": 2, "open": 1, "investigating": 1, "resolved": 0, "sev1Open": 1,
    }


def test_delete_then_404(client):
    a = client.post("/api/incidents", json={"title": "Flaky DNS"}).json()
    assert client.delete(f"/api/incidents/{a['id']}").status_code == 204
    assert client.get(f"/api/incidents/{a['id']}").status_code == 404
    assert client.put(f"/api/incidents/{a['id']}", json={"status": "RESOLVED"}).status_code == 404


def test_list_newest_first(client):
    client.post("/api/incidents", json={"title": "first"})
    client.post("/api/incidents", json={"title": "second"})
    assert [i["title"] for i in client.get("/api/incidents").json()] == ["second", "first"]


def test_metrics_exposed(client):
    client.get("/health")
    assert "http_requests_total" in client.get("/metrics").text
