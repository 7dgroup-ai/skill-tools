"""单元测试：priority/scorer（纯函数） + priority/runner（分批）。"""
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))

from priority.scorer import Weights, score  # noqa: E402
from priority.runner import partition  # noqa: E402


def test_score_formula():
    m = {"failure_rate": 0.30, "impact_score": 0.80, "duration_sec": 1.2, "max_duration_sec": 9.0}
    s = score(m)
    # 0.4*0.30 + 0.4*0.80 + 0.2*(1 - 1.2/9.0) = 0.12 + 0.32 + 0.173 = 0.613
    assert abs(s - 0.613) < 1e-3


def test_score_defaults_when_missing():
    """缺数据兜底：F=0.1、A=0.5、T=T_max，不报错。"""
    m = {"max_duration_sec": 9.0}
    s = score(m)
    # 0.4*0.1 + 0.4*0.5 + 0.2*(1 - 1.0) = 0.04 + 0.2 + 0 = 0.24
    assert abs(s - 0.24) < 1e-6


def test_score_pure_replayable():
    m = {"failure_rate": 0.1, "impact_score": 0.5, "duration_sec": 2.0, "max_duration_sec": 10.0}
    assert score(m) == score(m)  # 同一输入必得同一输出


def test_weights_sum_must_be_1():
    import pytest as pt
    with pt.raises(ValueError):
        Weights(failure=0.5, impact=0.5, time=0.5)


def test_partition_tiers_and_skipped():
    """P0(≥0.6) / P1(0.3~0.6) / P2(<0.3) / 超预算进 skipped。"""
    cases = [
        {"test_case": "t_p0", "failure_rate": 0.3, "impact_score": 0.8, "duration_sec": 1.0},   # 0.64 -> P0
        {"test_case": "t_p1", "failure_rate": 0.5, "impact_score": 0.2, "duration_sec": 3.0},   # 0.47 -> P1
        {"test_case": "t_p2", "failure_rate": 0.02, "impact_score": 0.05, "duration_sec": 0.8}, # 0.23 -> P2
        {"test_case": "t_skip", "failure_rate": 0.3, "impact_score": 0.8, "duration_sec": 100}, # 高分但超预算 -> skipped
    ]
    queue = partition(cases, time_budget_sec=5)  # t_p0+t_p1+t_p2 总耗时 4.8s 可装下
    assert "t_p0" in queue["batches"]["P0"]
    assert "t_p1" in queue["batches"]["P1"]
    assert "t_p2" in queue["batches"]["P2"]
    assert "t_skip" in queue["skipped"]  # skipped 非空（红线：绝不静默丢弃）


def test_partition_reproduces_with_same_input():
    cases = [{"test_case": "a", "failure_rate": 0.1, "impact_score": 0.9, "duration_sec": 1.0}]
    assert partition(cases) == partition(cases)