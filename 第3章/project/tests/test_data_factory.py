import pytest

from datafactory.builder import OrderBuilder
from datafactory.extractors import extract, schema_example
from datafactory.factory import DataFactory
from datafactory.provider import DataPoolExhausted, DataProvider, TTLCleaner


def _pool():
    return {
        "users": [{"id": 1}, {"id": 2}, {"id": 3}],
        "goods": [{"id": 101}, {"id": 102}, {"id": 103}, {"id": 104}],
    }


def test_builder_chain():
    order = (OrderBuilder().with_user(7)
             .with_goods([101, 102]).with_status("PENDING").build())
    assert order["user_id"] == 7
    assert order["goods_ids"] == [101, 102]
    assert order["total"] == 2 * 19.9
    assert order["status"] == "PENDING"


def test_factory_normal_order():
    factory = DataFactory(DataProvider(_pool()))
    order = factory.normal_order()
    assert order["status"] == "PENDING"
    assert len(order["goods_ids"]) == 3
    assert order["user_id"] in {1, 2, 3}


def test_provider_uniqueness_and_exhaustion():
    provider = DataProvider(_pool())
    got = {provider.unique_user()["id"] for _ in range(3)}
    assert got == {1, 2, 3}
    with pytest.raises(DataPoolExhausted):
        provider.unique_user()


def test_extract_jsonpath_and_regex():
    body = {"data": {"token": "abc123", "orders": [{"order_id": "o-1"}]}}
    assert extract("$.data.token", body) == "abc123"
    assert extract("$.data.orders[*].order_id", body, "jsonpath") == "o-1"
    assert extract(r'"order_id": "([^"]+)"', body, "regex") == "o-1"


def test_schema_example():
    schema = {"type": "object", "required": ["token"],
              "properties": {"token": {"type": "string"}, "expires_in": {"type": "integer"}}}
    example = schema_example(schema)
    assert example["token"] == "example"
    assert isinstance(example["expires_in"], int)


def test_ttl_cleaner():
    import time as _t
    cleaner = TTLCleaner(ttl=0)   # ttl=0：立即过期
    cleaner.register("order-1")
    assert cleaner.sweep() == 1
    cleaner2 = TTLCleaner(ttl=3600)
    cleaner2.register("order-2")
    assert cleaner2.sweep() == 0   # 未过期保留
