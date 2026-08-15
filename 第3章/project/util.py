"""轻量 JSONPath 子集实现：避免额外依赖，教学可读。

支持语法：
  $.a.b.c           逐级取字段
  $.data[*].id      遍历数组
  $.data[0].id      按下标取
  $.a['b']          字段名下标形式
"""

from __future__ import annotations

import re
from typing import Any

TOKEN = re.compile(r"(?P<dot>\.)|\['(?P<key>[^']+)'\]|\[\*(?P<star>)\]|\[(?P<idx>\d+)\]|(?P<root>\$)|(?P<name>[A-Za-z_][A-Za-z0-9_]*)")

def _parse(path: str) -> list[str | int | slice]:
    steps: list[str | int | slice] = []
    pos = 0
    for m in TOKEN.finditer(path):
        if m.start() != pos:
            raise ValueError(f"无法解析的路径段: {path[pos:m.start()]!r} in {path!r}")
        pos = m.end()
        if m.group("root"):
            continue
        if m.group("key"):
            steps.append(m.group("key"))
        elif m.group("star") is not None:
            steps.append(slice(None))
        elif m.group("idx") is not None:
            steps.append(int(m.group("idx")))
        elif m.group("dot"):
            continue
        elif m.group("name"):
            steps.append(m.group("name"))
    return steps


def jsonpath_get(data: Any, path: str) -> Any:
    """按 JSONPath 取字段，返回单值（取第一个匹配）。"""
    steps = _parse(path)
    current = [data]
    for step in steps:
        nxt: list[Any] = []
        for item in current:
            if isinstance(step, slice):
                if isinstance(item, list):
                    nxt.extend(item)
            elif isinstance(step, int):
                if isinstance(item, list) and step < len(item):
                    nxt.append(item[step])
            else:
                if isinstance(item, dict) and step in item:
                    nxt.append(item[step])
        current = nxt
        if not current:
            raise KeyError(f"{path}: 字段不存在")
    return current[0]


def jsonpath_all(data: Any, path: str) -> list[Any]:
    """按 JSONPath 取全部匹配。"""
    steps = _parse(path)
    current = [data]
    for step in steps:
        nxt: list[Any] = []
        for item in current:
            if isinstance(step, slice):
                if isinstance(item, list):
                    nxt.extend(item)
            elif isinstance(step, int):
                if isinstance(item, list) and step < len(item):
                    nxt.append(item[step])
            else:
                if isinstance(item, dict) and step in item:
                    nxt.append(item[step])
        current = nxt
    return current
