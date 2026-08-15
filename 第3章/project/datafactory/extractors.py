from __future__ import annotations

import re
from typing import Any

from util import jsonpath_get


def extract(path: str, source: Any, method: str = "jsonpath") -> Any:
    """统一提取入口：method ∈ {jsonpath, regex, schema}。"""
    if method == "jsonpath":
        return jsonpath_get(source, path)
    if method == "regex":
        if isinstance(source, (dict, list)):
            import json
            source = json.dumps(source, ensure_ascii=False)
        m = re.search(path, source)
        if not m:
            raise KeyError(f"regex {path!r} 未匹配")
        return m.group(1)
    if method == "schema":
        return schema_example(path)
    raise ValueError(f"unknown method: {method}")


def extract_all(path: str, source: Any, method: str = "jsonpath") -> list[Any]:
    if method == "jsonpath":
        from util import jsonpath_all
        return jsonpath_all(source, path)
    value = extract(path, source, method)
    return [value]


def schema_example(schema: Any, depth: int = 0) -> Any:
    """从 JSON Schema 取“示例值”，用于造数。"""
    if depth > 3:
        return None
    if isinstance(schema, bool):
        return schema
    stype = schema.get("type")
    if stype == "object":
        return {k: schema_example(v, depth + 1)
                for k, v in schema.get("properties", {}).items()
                if k in schema.get("required", []) or True}
    if stype == "array":
        return [schema_example(schema.get("items", {}), depth + 1)]
    if stype == "integer":
        return schema.get("minimum") or schema.get("default") or 1
    if stype == "number":
        return schema.get("default") or 1.0
    if stype == "boolean":
        return schema.get("default", True)
    if stype == "string":
        enum = schema.get("enum")
        return enum[0] if enum else (schema.get("default") or "example")
    return None
