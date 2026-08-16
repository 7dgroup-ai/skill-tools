"""用例智能优先级排序（Skill-12）· 优先级队列：按时间预算贪心分批 P0/P1/P2。

用法：
    python -m priority.runner --metrics build/test_metrics.json \
        --time-budget 1800 --out build/queue.json

输出 build/queue.json：{batches:{P0:[],P1:[],P2:[]}, skipped:[]}
三条纪律（§4.4.2）：
1. skipped 绝不静默丢弃 —— 必须显性输出
2. 失败自动重跑 —— 由 CI 侧 --lf/--ff 消费（本模块只管分批）
3. 全量兜底 —— 夜间 P2 全量，逃逸率 > 1% 降级回全量
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from .scorer import Weights, score


def partition(metrics_list: List[Dict[str, Any]],
              p0_threshold: float = 0.6,
              p1_threshold: float = 0.3,
              time_budget_sec: int = 1800) -> Dict[str, Any]:
    """贪心装桶：score 降序遍历，累加 duration_sec，不超预算进 P0→P1→P2；
    超出预算的全部进 skipped（skipped 非空时必须显性输出）。
    """
    weights = Weights.from_env()
    # 预计算 T_max
    t_max = max((m.get("duration_sec", 0) for m in metrics_list), default=0) or 1.0
    scored = []
    for m in metrics_list:
        m = dict(m)
        m["max_duration_sec"] = m.get("max_duration_sec", t_max)
        scored.append({
            "test_case": m["test_case"],
            "score": score(m, weights),
            "duration_sec": m.get("duration_sec", t_max),
        })
    scored.sort(key=lambda x: x["score"], reverse=True)

    batches: Dict[str, List[str]] = {"P0": [], "P1": [], "P2": []}
    skipped: List[str] = []
    used = 0.0

    for item in scored:
        if used + item["duration_sec"] > time_budget_sec:
            skipped.append(item["test_case"])
            continue
        used += item["duration_sec"]
        if item["score"] >= p0_threshold:
            batches["P0"].append(item["test_case"])
        elif item["score"] >= p1_threshold:
            batches["P1"].append(item["test_case"])
        else:
            batches["P2"].append(item["test_case"])

    return {
        "time_budget_sec": time_budget_sec,
        "used_sec": round(used, 2),
        "batches": batches,
        "skipped": skipped,
    }


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="按时间预算分批生成优先级队列")
    ap.add_argument("--metrics", required=True, help="用例指标 JSON（[{test_case,failure_rate,impact_score,duration_sec}]）")
    ap.add_argument("--time-budget", type=int, default=1800)
    ap.add_argument("--out", default="build/queue.json")
    args = ap.parse_args(argv)

    metrics_list = json.loads(Path(args.metrics).read_text())
    queue = partition(metrics_list, time_budget_sec=args.time_budget)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(queue, ensure_ascii=False, indent=2))
    print(f"[runner] 预算={queue['time_budget_sec']}s 已用={queue['used_sec']}s")
    for tier in ("P0", "P1", "P2"):
        print(f"  {tier}: {len(queue['batches'][tier])} 条")
    print(f"  skipped: {len(queue['skipped'])} 条（必须显性上报，见 build/skipped.txt）")
    if queue["skipped"]:
        Path(args.out).parent.joinpath("skipped.txt").write_text(
            "\n".join(queue["skipped"]) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())