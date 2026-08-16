"""精准选测（Skill-09）· 用例推荐器：变更方法集 → impact_map 查询 → 冒烟集合并。

用法：
    python -m selection.recommender --changes build/method_changes.json \
        --impact-map build/impact_map.db --out build/test_list.txt

推荐规则（§4.1.2）：
1. 变更方法集 M → 查 impact_map 得到候选用例 U(M)
2. 静态兜底：与变更文件同名的 test_*.py 全量加入
3. 冒烟集永远全量（8 步链路用例，不进选测）
4. 输出 test_list.txt 交给 CI 消费（pytest $(cat test_list.txt)）

验收红线：召回率 ≥ 90%、准确率 ≥ 80%；单次推荐 < 10s。
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import List, Optional

# 冒烟集：8 步核心链路用例，永远全量、永远第一批跑（§4.1.3 兜底规则）
SMOKE_CASES = [
    "test_sketch_api::test_smoke_8step_chain",
    "test_sketch_api::test_login_ok",
    "test_sketch_api::test_login_wrong_pwd",
    "test_sketch_api::test_goods_list",
    "test_sketch_api::test_cart_add_ok",
    "test_sketch_api::test_cart_add_bad_goods",
    "test_sketch_api::test_order_preview",
    "test_sketch_api::test_order_pay_idempotent",
    "test_sketch_api::test_order_query_paid",
]

IMPACT_SCHEMA = """
CREATE TABLE IF NOT EXISTS impact_map (
    test_case    TEXT NOT NULL,
    source_file  TEXT NOT NULL,
    source_func  TEXT NOT NULL,
    last_seen    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (test_case, source_file, source_func)
);
CREATE INDEX IF NOT EXISTS idx_src ON impact_map(source_file, source_func);
"""


def init_impact_map(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.executescript(IMPACT_SCHEMA)
    return conn


def upsert(conn: sqlite3.Connection, rows: List[tuple]) -> None:
    """rows: [(test_case, source_file, source_func), ...]，upsert 更新 last_seen。"""
    conn.executemany(
        """INSERT INTO impact_map (test_case, source_file, source_func)
           VALUES (?, ?, ?)
           ON CONFLICT(test_case, source_file, source_func)
           DO UPDATE SET last_seen = CURRENT_TIMESTAMP""",
        rows,
    )
    conn.commit()


def expire_stale(conn: sqlite3.Connection, days: int = 7) -> int:
    """过期清理：last_seen 超过 N 天的映射删除（§4.1.2 生命周期阶段③）。"""
    cur = conn.execute(
        "DELETE FROM impact_map WHERE last_seen < datetime('now', ?)",
        (f"-{days} days",),
    )
    conn.commit()
    return cur.rowcount


def recommend(changes: List[dict],
              db_path: Path,
              smoke_cases: Optional[List[str]] = None) -> List[str]:
    """变更方法集 M → 推荐用例集 U(M)，合并冒烟集（去重保序）。"""
    smoke = smoke_cases if smoke_cases is not None else SMOKE_CASES
    if not changes:
        return list(smoke)  # 无变更（文档类 PR）也至少跑冒烟

    db_path = Path(db_path)
    if not db_path.exists():
        return list(smoke)

    conn = init_impact_map(db_path)
    try:
        selected = set(smoke)
        for ch in changes:
            rows = conn.execute(
                """SELECT test_case FROM impact_map
                   WHERE source_file = ? AND (source_func = ? OR ? = '')""",
                (ch["file"], ch.get("method", ""), ch.get("method", "")),
            ).fetchall()
            for r in rows:
                selected.add(r[0])

            # 静态兜底：文件名匹配 test_<basename>.py
            stem = Path(ch["file"]).stem
            rows = conn.execute(
                """SELECT test_case FROM impact_map
                   WHERE test_case LIKE ?""",
                (f"%{stem}%",),
            ).fetchall()
            for r in rows:
                selected.add(r[0])
        return list(selected)
    finally:
        conn.close()


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="用例推荐器：变更方法集 → 动态用例集")
    ap.add_argument("--changes", required=True, help="ast_diff 输出 JSON")
    ap.add_argument("--impact-map", default="build/impact_map.db", help="impact_map SQLite")
    ap.add_argument("--out", default="build/test_list.txt")
    ap.add_argument("--smoke", action="store_true", help="只输出冒烟集（跳过推荐）")
    args = ap.parse_args(argv)

    changes = json.loads(Path(args.changes).read_text())
    cases = SMOKE_CASES if args.smoke else recommend(changes, Path(args.impact_map))

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(cases) + "\n")
    print(f"[recommender] 推荐用例 {len(cases)} 条 -> {out}")
    for c in cases:
        print(f"  {c}")
    return 0


if __name__ == "__main__":
    sys.exit(main())