from __future__ import annotations


class OrderBuilder:
    """Builder：逐字段构造订单，返回可复用构造器。"""

    def __init__(self):
        self._order = {"user_id": 0, "goods_ids": [], "total": 0.0, "status": "PENDING"}

    def with_user(self, user_id: int) -> "OrderBuilder":
        self._order["user_id"] = user_id
        return self

    def with_goods(self, goods_ids: list[int]) -> "OrderBuilder":
        self._order["goods_ids"] = list(goods_ids)
        self._order["total"] = round(len(goods_ids) * 19.9, 2)
        return self

    def with_status(self, status: str) -> "OrderBuilder":
        self._order["status"] = status
        return self

    def with_total(self, total: float) -> "OrderBuilder":
        self._order["total"] = total
        return self

    def build(self) -> dict:
        return dict(self._order)


class UserBuilder:
    """Builder：构造用户。"""

    def __init__(self):
        self._user = {"id": 0, "username": "", "role": "customer"}

    def with_id(self, uid: int) -> "UserBuilder":
        self._user["id"] = uid
        return self

    def with_username(self, name: str) -> "UserBuilder":
        self._user["username"] = name
        return self

    def build(self) -> dict:
        return dict(self._user)
