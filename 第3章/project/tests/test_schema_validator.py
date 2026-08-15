import pytest

from asserters.business_assert import BusinessAssert
from asserters.schema_validator import USER_LOGIN_SCHEMA, assert_schema
from clients.base import ApiResponse


def test_valid_login_body_passes_schema():
    assert_schema(
        {"code": 0, "data": {"token": "x" * 40, "expires_in": 3600}},
        USER_LOGIN_SCHEMA,
    )


def test_missing_token_fails_schema():
    with pytest.raises(Exception):
        assert_schema({"code": 0, "data": {}}, USER_LOGIN_SCHEMA)


def test_short_token_fails_schema():
    with pytest.raises(Exception):
        assert_schema({"code": 0, "data": {"token": "short", "expires_in": 3600}},
                      USER_LOGIN_SCHEMA)


def test_business_assert_chain():
    resp = ApiResponse(status_code=200, body={"code": 0, "data": {"token": "t" * 40}})
    (BusinessAssert(resp).http_ok().biz_code(0)
     .field("$.data.token", predicate=lambda t: len(t) >= 20))


def test_business_assert_bad_code_fails():
    resp = ApiResponse(status_code=200, body={"code": 1001, "msg": "登录失败"})
    with pytest.raises(AssertionError):
        BusinessAssert(resp).biz_code(0)


def test_business_assert_field_missing():
    resp = ApiResponse(status_code=200, body={"code": 0, "data": {}})
    with pytest.raises(Exception):
        BusinessAssert(resp).field("$.data.token")
