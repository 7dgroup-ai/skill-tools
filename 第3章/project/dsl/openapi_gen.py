"""OpenAPI/Swagger 驱动用例生成：骨架 + 参数组合。"""

from __future__ import annotations

from typing import Any


def gen_scenarios_from_openapi(spec: dict, base_url: str) -> list[dict]:
    """遍历 OpenAPI paths，为每个 op 生成 YAML 场景骨架。

    说明：只生成“骨架”，业务断言（biz_code / 字段关系）必须人工补充。
    """
    out: list[dict] = []
    for path, item in spec.get("paths", {}).items():
        for method, op in item.items():
            if method not in {"get", "post", "put", "patch", "delete"}:
                continue
            params = [p["name"] for p in op.get("parameters", [])]
            body_schema = (op.get("requestBody", {}).get("content", {})
                           .get("application/json", {}).get("schema"))
            out.append({
                "name": op.get("operationId", f"{method}_{path.replace('/', '_')}"),
                "base_url": base_url,
                "steps": [{
                    "name": op.get("operationId", f"{method}_{path.replace('/', '_')}"),
                    "request": {
                        "path": path,
                        "method": method.upper(),
                        "params": {p: "${" + p + "}" for p in params},
                        **({"body": body_schema} if body_schema else {}),
                    },
                    "assert": {"http_ok": True},
                }],
            })
    return out
