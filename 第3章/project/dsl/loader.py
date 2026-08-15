from __future__ import annotations

from typing import Any

import yaml


def load_scenario(path: str) -> dict:
    """加载 YAML 场景并做基本结构校验。"""
    with open(path, "r", encoding="utf-8") as f:
        scenario = yaml.safe_load(f)
    _validate(scenario)
    return scenario


def _validate(s: dict) -> None:
    assert "name" in s, "场景缺少 name"
    assert isinstance(s.get("steps"), list) and s["steps"], "场景 steps 必须为非空列表"
    for step in s["steps"]:
        assert "request" in step, f"步骤 {step.get('name')} 缺少 request"
        assert "path" in step["request"], f"步骤 {step.get('name')} request 缺少 path"
