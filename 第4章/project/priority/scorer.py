"""用例智能优先级排序（Skill-12）· 三维因子评分：F(历史失败率)+A(变更关联度)+T(执行时间)。

纯函数，无 I/O、无副作用、可单测回放：
    score = w_f*F + w_a*A + w_t*(1 - T/T_max)
缺数据兜底：F=0.1、A=0.5、T=T_max（最保守，不因缺数据报错）。
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class Weights:
    failure: float = 0.40
    impact: float = 0.40
    time: float = 0.20

    def __post_init__(self):
        if abs(self.failure + self.impact + self.time - 1.0) > 1e-6:
            raise ValueError(f"权重和必须为 1，当前 {self.failure + self.impact + self.time}")

    @classmethod
    def from_env(cls, env: Optional[Dict[str, str]] = None) -> "Weights":
        """权重外部化：环境变量 WEIGHT_FAILURE / WEIGHT_IMPACT / WEIGHT_TIME 覆盖（§4.4 权重外部化）。"""
        env = env or os.environ
        return cls(
            failure=float(env.get("WEIGHT_FAILURE", 0.40)),
            impact=float(env.get("WEIGHT_IMPACT", 0.40)),
            time=float(env.get("WEIGHT_TIME", 0.20)),
        )


def score(metrics: Dict[str, Any], weights: Weights = Weights()) -> float:
    """纯函数：同一输入必得同一输出。

    metrics 字段：
        test_case       用例名
        failure_rate    F ∈ [0,1]，近 30 天失败次数/执行次数（缺省 0.1）
        impact_score    A ∈ [0,1]，本次变更命中强度（缺省 0.5）
        duration_sec    T 最近一次执行耗时（缺省 T_max）
        max_duration_sec T_max 全部用例最大耗时
    """
    t_max = metrics.get("max_duration_sec", 0) or 1.0
    F = metrics.get("failure_rate", 0.1)
    A = metrics.get("impact_score", 0.5)
    T = metrics.get("duration_sec", t_max)
    return round(weights.failure * F + weights.impact * A + weights.time * (1 - T / t_max), 6)