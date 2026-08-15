from __future__ import annotations

from typing import Any, Callable

from clients.base import ApiResponse
from util import jsonpath_get


class BusinessAssert:
    """业务断言链：状态码 → 业务码 → 字段等值/谓词，链式组合。"""

    def __init__(self, resp: ApiResponse):
        self._resp = resp
        self._body: Any = resp.body

    @property
    def body(self) -> Any:
        return self._body

    def http_ok(self) -> "BusinessAssert":
        assert self._resp.ok, f"HTTP {self._resp.status_code} 非 2xx"
        return self

    def http_code(self, expect: int) -> "BusinessAssert":
        assert self._resp.status_code == expect, \
            f"HTTP 期望 {expect}，实际 {self._resp.status_code}"
        return self

    def biz_code(self, expect: int = 0) -> "BusinessAssert":
        actual = self._body.get("code") if isinstance(self._body, dict) else None
        assert actual == expect, f"业务码期望 {expect}，实际 {actual}"
        return self

    def field(self, path: str, expect: Any = None, predicate: Callable[[Any], bool] | None = None) -> "BusinessAssert":
        value = jsonpath_get(self._body, path)
        if expect is not None:
            assert value == expect, f"{path}={value} != {expect}"
        if predicate is not None:
            assert predicate(value), f"{path} 未通过谓词: {value!r}"
        return self

    def has(self, path: str) -> "BusinessAssert":
        jsonpath_get(self._body, path)  # 不存在则抛 KeyError
        return self
