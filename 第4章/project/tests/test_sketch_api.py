"""8 步链路接口用例（冒烟集 + 覆盖率采集驱动）。

对象：sketch-store FastAPI 应用（app/ 包）。
跑法：cd 第4章/project && coverage run --branch -m pytest tests/test_sketch_api.py
覆盖率以 sketch-store 的 app/ 为被测对象（--source=.../sketch-store/app）。

冒烟集永远全量（§4.1.3）：test_smoke_8step_chain 即 8 步核心链路。
"""
import os
import sys
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# 指向 sketch-store 被测应用（skill 根目录/projects/sketch-store）
SKILL_ROOT = Path(__file__).resolve().parents[3]
SKETCH_ROOT = SKILL_ROOT / "projects" / "sketch-store"
sys.path.insert(0, str(SKETCH_ROOT))

# 用临时 DB，避免污染铺底数据；seed 需要真实账号
_tmpdb = tempfile.mkdtemp()
os.environ["DB_FILE"] = str(Path(_tmpdb) / "mall.db")

from app.main import app  # noqa: E402
from app.seeded import seed  # noqa: E402

seed("local")
_client = TestClient(app)

USER = "user00001"
PASS = "pass00001"


def _login() -> str:
    r = _client.post("/api/login", json={"username": USER, "password": PASS})
    assert r.status_code == 200 and r.json()["code"] == 0
    return r.json()["data"]["token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


_login_counter = [0]


def _fresh_user() -> tuple[str, str]:
    """每个用例用独立用户，避免购物车/订单状态串扰。"""
    import hashlib
    from app import models
    _login_counter[0] += 1
    username = f"tuser{_login_counter[0]:04d}"
    password = f"tpw{_login_counter[0]:04d}"
    models.insert_user(username, hashlib.sha256(password.encode()).hexdigest(), username)
    r = _client.post("/api/login", json={"username": username, "password": password})
    assert r.json()["code"] == 0
    return username, r.json()["data"]["token"]


# ---------- 冒烟集（§4.1.3：永远全量） ----------

def test_smoke_8step_chain():
    """8 步核心链路：商品列表→登录→加购→查车→预览→建单→支付→查单。"""
    # 1 商品列表
    r = _client.get("/api/goods/list?page=1&size=5")
    assert r.status_code == 200 and r.json()["code"] == 0
    # 2 登录
    token = _login()
    # 3 加购
    r = _client.post("/api/cart/add", json={"goods_id": 1, "num": 2}, headers=_auth(token))
    assert r.json()["code"] == 0
    # 4 查车
    r = _client.get("/api/cart/list", headers=_auth(token))
    assert r.json()["data"]["total"] == 3.98
    # 5 预览
    r = _client.post("/api/order/preview", json={}, headers=_auth(token))
    order_id = r.json()["data"]["order_id"]
    # 6 建单
    r = _client.post("/api/order/create", json={"order_id": order_id}, headers=_auth(token))
    assert r.json()["data"]["status"] == "CREATED"
    # 7 支付
    r = _client.post("/api/order/pay", json={"order_id": order_id, "pay_type": "mock",
                                             "request_id": "smoke-1"}, headers=_auth(token))
    assert r.json()["data"]["ok"] is True
    # 8 查单（断言 PAID）
    r = _client.get(f"/api/order/{order_id}", headers=_auth(token))
    assert r.json()["data"]["status"] == "PAID"


# ---------- 登录 ----------

def test_login_ok():
    assert _login()


def test_login_wrong_pwd():
    r = _client.post("/api/login", json={"username": USER, "password": "wrong"})
    assert r.json()["code"] == 1


# ---------- 商品 ----------

def test_goods_list_page():
    r = _client.get("/api/goods/list?page=2&size=10")
    assert r.json()["code"] == 0 and len(r.json()["data"]["list"]) == 10


def test_goods_list_pagination_boundary():
    r = _client.get("/api/goods/list?page=0&size=0")
    assert r.status_code == 422  # Query ge=1 校验


# ---------- 购物车 ----------

def test_cart_add_ok():
    _, token = _fresh_user()
    r = _client.post("/api/cart/add", json={"goods_id": 2, "num": 1}, headers=_auth(token))
    assert r.json()["code"] == 0


def test_cart_add_bad_goods():
    _, token = _fresh_user()
    r = _client.post("/api/cart/add", json={"goods_id": 999999, "num": 1}, headers=_auth(token))
    assert r.json()["code"] == 1 and "不存在" in r.json()["msg"]


def test_cart_add_bad_num():
    _, token = _fresh_user()
    r = _client.post("/api/cart/add", json={"goods_id": 1, "num": 0}, headers=_auth(token))
    assert r.json()["code"] == 1


def test_cart_add_no_stock():
    _, token = _fresh_user()
    r = _client.post("/api/cart/add", json={"goods_id": 1, "num": 99999}, headers=_auth(token))
    assert r.json()["code"] == 1 and "库存不足" in r.json()["msg"]


def test_cart_list_requires_auth():
    r = _client.get("/api/cart/list")
    assert r.status_code == 401


# ---------- 订单 ----------

def test_order_preview_empty_cart():
    _, token = _fresh_user()
    r = _client.post("/api/order/preview", json={}, headers=_auth(token))
    assert r.json()["code"] == 1 and "购物车为空" in r.json()["msg"]


def test_order_create_missing_id():
    _, token = _fresh_user()
    r = _client.post("/api/order/create", json={}, headers=_auth(token))
    assert r.json()["code"] == 1


def test_order_create_not_exist():
    _, token = _fresh_user()
    r = _client.post("/api/order/create", json={"order_id": "NOPE"}, headers=_auth(token))
    assert r.json()["code"] == 1 and "不存在" in r.json()["msg"]


def test_order_pay_idempotent():
    """同一 request_id 重复支付幂等（§4.4 稳定性验证）。"""
    _, token = _fresh_user()
    _client.post("/api/cart/add", json={"goods_id": 3, "num": 1}, headers=_auth(token))
    order_id = _client.post("/api/order/preview", json={}, headers=_auth(token)).json()["data"]["order_id"]
    r1 = _client.post("/api/order/pay", json={"order_id": order_id, "request_id": "dup-1"}, headers=_auth(token))
    r2 = _client.post("/api/order/pay", json={"order_id": order_id, "request_id": "dup-1"}, headers=_auth(token))
    assert r1.json()["data"]["ok"] is True
    assert r2.json()["data"]["ok"] is True  # 幂等：不报错


def test_order_query_not_exist():
    _, token = _fresh_user()
    r = _client.get("/api/order/ORD-NOT-EXIST", headers=_auth(token))
    assert r.json()["code"] == 1


# ---------- 运维 ----------

def test_health():
    r = _client.get("/health")
    assert r.status_code == 200 and r.json()["status"] == "UP"


def test_metrics():
    r = _client.get("/metrics")
    assert r.status_code == 200 and "sketch_http_requests_total" in r.text


def test_switch_latency_sim():
    r = _client.post("/api/switch", json={"switch": "latency_sim", "on": False})
    assert r.json()["code"] == 0
    assert r.json()["data"]["latency_sim"] is False


def test_switch_sql_injection_off():
    r = _client.post("/api/switch", json={"switch": "sql_injection", "on": False})
    assert r.json()["code"] == 0
    # 关掉后 SQL 注入不再生效
    r = _client.post("/api/login", json={"username": "user00001' --", "password": "x"})
    assert r.json()["code"] == 1