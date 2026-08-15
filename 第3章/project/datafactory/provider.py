from __future__ import annotations

import time
from collections import defaultdict
from typing import Any


class DataPoolExhausted(Exception):
    """数据池耗尽。"""


class DataProvider:
    """Provider：数据池管理 + 唯一性保障 + 消费标记。"""

    def __init__(self, pool: dict[str, list[dict]] | None = None):
        self._pool: dict[str, list[dict]] = pool or {}
        self._cursor: dict[str, int] = defaultdict(int)
        self._used: set[Any] = set()

    @property
    def used(self) -> set[Any]:
        return self._used

    def unique_user(self) -> dict:
        users = self._pool.get("users", [])
        for _ in range(len(users)):
            u = users[self._cursor["users"] % len(users)]
            self._cursor["users"] += 1
            if u["id"] not in self._used:
                self._used.add(u["id"])
                return u
        raise DataPoolExhausted("users 数据池耗尽")

    def any_goods(self, n: int) -> list[dict]:
        return self._pool.get("goods", [])[:n]

    def pool(self, key: str) -> list[dict]:
        return self._pool.get(key, [])


class TTLCleaner:
    """TTL 清理器：登记造数 key，到期自动清扫。"""

    def __init__(self, ttl: int = 3600):
        self._ttl = ttl
        self._records: list[tuple[str, float]] = []

    def register(self, key: str) -> None:
        self._records.append((key, time.time()))

    def sweep(self) -> int:
        now = time.time()
        keep: list[tuple[str, float]] = []
        removed = 0
        for key, ts in self._records:
            if now - ts < self._ttl:
                keep.append((key, ts))
            else:
                removed += 1
        self._records = keep
        return removed

    @property
    def size(self) -> int:
        return len(self._records)
