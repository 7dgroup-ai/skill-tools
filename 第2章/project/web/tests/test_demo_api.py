"""Demo 前端接口单测：无浏览器也能跑（验证被测前端本身可用）。"""

import httpx
from fastapi.testclient import TestClient

from demo_app.main import app

client = TestClient(app)


def test_health():
    assert client.get("/health").json()["code"] == 0


def test_index_serves_page():
    resp = client.get("/")
    assert resp.status_code == 200
    assert "登录" in resp.text


def test_login_ok_sets_cookie():
    resp = client.post("/api/login", json={"username": "u_1001", "password": "pass_1001"})
    assert resp.json()["code"] == 0
    assert "demo_sid" in resp.cookies


def test_login_error_msg():
    resp = client.post("/api/login", json={"username": "u_1001", "password": "wrong"})
    assert resp.json()["code"] == 1001


def test_checkout_flow_via_api():
    login = client.post("/api/login", json={"username": "u_1001", "password": "pass_1001"})
    sid = login.cookies["demo_sid"]
    cookies = {"demo_sid": sid}

    add = client.post("/api/cart/add", json={"goods_id": "g_2001", "num": 1}, cookies=cookies)
    assert add.json()["code"] == 0

    checkout = client.post("/api/checkout", cookies=cookies)
    assert checkout.json()["code"] == 0
    assert checkout.json()["data"]["order_id"].startswith("order-")

    count = client.get("/api/orders/count").json()["data"]["count"]
    assert count >= 1


def test_unauthorized_cart_returns_401():
    fresh = TestClient(app)   # 独立客户端，避免复用前序用例的登录 cookie
    resp = fresh.get("/api/cart")
    assert resp.status_code == 401
