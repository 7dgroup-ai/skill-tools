from fastapi.testclient import TestClient

from mocks.app import app

client = TestClient(app)


def test_pay_ok():
    resp = client.post("/pay", params={"fail_rate": 0.0})
    assert resp.status_code == 200
    assert resp.json()["code"] == 0


def test_pay_always_fail():
    resp = client.post("/pay", params={"fail_rate": 1.0})
    assert resp.status_code == 503
    assert resp.json()["code"] == -1


def test_pay_delay_injectable():
    resp = client.post("/pay", params={"delay_ms": 10})
    assert resp.status_code == 200


def test_health():
    resp = client.get("/health")
    assert resp.json()["code"] == 0
