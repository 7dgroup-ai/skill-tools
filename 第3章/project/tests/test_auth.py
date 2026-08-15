import pytest

from clients.auth import AuthManager, JwtStrategy
from clients.base import ApiRequest
from clients.http_client import HttpClient
from tests.fake_store import make_transport


@pytest.fixture()
def raw_client():
    return HttpClient("http://fake", transport=make_transport())


def test_jwt_strategy_acquires_token(raw_client):
    strategy = JwtStrategy(raw_client, "u_1001", "pass_1001")
    token = strategy.acquire()
    assert token and len(token) >= 20
    assert strategy.can_refresh() is True


def test_jwt_strategy_bad_login_raises(raw_client):
    strategy = JwtStrategy(raw_client, "u_1001", "bad-pass")
    with pytest.raises(PermissionError):
        strategy.acquire()


def test_auth_manager_injects_token(raw_client):
    manager = AuthManager(JwtStrategy(raw_client, "u_1001", "pass_1001"))
    req = ApiRequest("/api/cart/list", "GET")
    injected = manager.ensure(req)
    assert injected.headers["Authorization"]  # token 已自动注入
    # 未登录时该接口应 401，注入后应 200
    resp = raw_client.request(injected)
    assert resp.status_code == 200
    assert resp.body["code"] == 0
