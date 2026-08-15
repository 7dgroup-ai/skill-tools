import httpx
import pytest

from clients.base import ApiRequest
from clients.http_client import HttpClient
from tests.fake_store import make_transport


@pytest.fixture()
def client():
    c = HttpClient("http://fake", transport=make_transport())
    yield c
    c.close()


def test_get_goods_list_ok(client):
    resp = client.request(ApiRequest("/api/goods/list", "GET", params={"page": 1, "size": 2}))
    assert resp.ok
    assert resp.body["code"] == 0
    assert resp.body["data"]["total"] == 5


def test_login_and_http_ok(client):
    resp = client.request(ApiRequest(
        "/api/login", "POST", body={"username": "u_1001", "password": "pass_1001"}))
    assert resp.ok
    assert resp.body["code"] == 0
    assert len(resp.body["data"]["token"]) >= 20


def test_bad_login_biz_code(client):
    resp = client.request(ApiRequest(
        "/api/login", "POST", body={"username": "u_1001", "password": "wrong"}))
    assert resp.ok                 # HTTP 200
    assert resp.body["code"] == 1001   # 但业务码失败


def test_elapsed_ms_recorded(client):
    resp = client.request(ApiRequest("/api/goods/list"))
    assert resp.elapsed_ms >= 0
