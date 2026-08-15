"""OpenAPI Diff：变更检测与破坏性判定。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Change:
    target: str          # path 或 path.field
    kind: str            # 变更类型
    breaking: bool       # 是否破坏性


def diff_compat(old: dict, new: dict) -> list[Change]:
    """对比新旧 OpenAPI，按“破坏性/兼容性”输出变更列表。"""
    changes: list[Change] = []
    old_paths, new_paths = old.get("paths", {}), new.get("paths", {})

    for p in sorted(set(old_paths) - set(new_paths)):
        changes.append(Change(p, "remove_path", breaking=True))

    for p in sorted(set(new_paths) - set(old_paths)):
        changes.append(Change(p, "add_path", breaking=False))

    for p in sorted(set(old_paths) & set(new_paths)):
        old_item, new_item = old_paths[p], new_paths[p]
        for method in set(old_item) & set(new_item):
            _diff_operation(p, method, old_item[method], new_item[method], changes)
    return changes


def _diff_operation(path: str, method: str, old_op: dict, new_op: dict,
                    changes: list[Change]) -> None:
    tag = f"{method.upper()} {path}"
    old_req, new_req = old_op.get("requestBody"), new_op.get("requestBody")
    old_schema = _schema_of(old_req)
    new_schema = _schema_of(new_req)
    old_required = set((old_schema or {}).get("required", []))
    new_required = set((new_schema or {}).get("required", []))

    for f in sorted(old_required - new_required):
        changes.append(Change(f"{tag}.{f}", "required_removed", breaking=True))
    for f in sorted(new_required - old_required):
        changes.append(Change(f"{tag}.{f}", "required_added", breaking=True))

    old_props, new_props = (old_schema or {}).get("properties", {}), \
                           (new_schema or {}).get("properties", {})
    for f in sorted(set(old_props) - set(new_props)):
        changes.append(Change(f"{tag}.{f}", "field_removed", breaking=True))


def _schema_of(req_body) -> dict | None:
    if not req_body:
        return None
    return req_body.get("content", {}).get("application/json", {}).get("schema")
