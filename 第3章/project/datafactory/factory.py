from __future__ import annotations

from .builder import OrderBuilder, UserBuilder
from .provider import DataProvider, DataPoolExhausted


class DataFactory:
    """Factory：按业务语义取数，隐藏构造细节。"""

    def __init__(self, provider: DataProvider):
        self._p = provider

    def normal_order(self) -> dict:
        user = self._p.unique_user()
        goods = self._p.any_goods(3)
        return (OrderBuilder()
                .with_user(user["id"])
                .with_goods([g["id"] for g in goods])
                .build())

    def order_of_user(self, user_id: int, status: str = "PAID") -> dict:
        goods = self._p.any_goods(1)
        return (OrderBuilder()
                .with_user(user_id)
                .with_goods([goods[0]["id"]])
                .with_status(status)
                .build())

    def paid_order(self) -> dict:
        order = self.normal_order()
        order["status"] = "PAID"
        return order

    def user(self, username: str) -> dict:
        return UserBuilder().with_username(username).build()
