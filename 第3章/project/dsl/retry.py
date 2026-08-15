from __future__ import annotations

import itertools
from typing import Any


def variant_cases(step: str, base: dict, variations: dict[str, list[dict]]) -> list[dict]:
    """单缺陷（正交）变体生成：一次只变一个维度，其余取基准值。

    base: 基准参数；variations: {"param": [{delta}, {delta2}]}
    返回每个变体 = 基准 + 单个维度的 delta。
    """
    cases: list[dict] = []
    for param, deltas in variations.items():
        for delta in deltas:
            case = dict(base)
            case.update(delta)
            cases.append({"step": step, "name": f"{param}-{case.get(param)}", "params": case})
    return cases


def cartesian_cases(step: str, params: dict[str, list[Any]]) -> list[dict]:
    """全组合（穷举）变体生成：所有取值笛卡尔积。"""
    keys, values = list(params.keys()), list(params.values())
    cases = []
    for combo in itertools.product(*values):
        case = dict(zip(keys, combo))
        cases.append({"step": step, "name": "-".join(f"{k}={v}" for k, v in case.items()),
                      "params": case})
    return cases
