#!/usr/bin/env python3
"""生成压测数据池：data/users.json + data/goods.json（与 seed 库保持一致）。
用法: python gen_data.py  （输出到 loadtest/data/）"""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

USER_COUNT = 500
GOODS_COUNT = 1000


def main():
    out = Path(__file__).resolve().parent / "data"
    out.mkdir(exist_ok=True)
    users = [
        {"username": f"user{i:05d}", "password": f"pass{i:05d}"}
        for i in range(1, USER_COUNT + 1)
    ]
    goods = [{"goods_id": i} for i in range(1, GOODS_COUNT + 1)]
    (out / "users.json").write_text(json.dumps(users, ensure_ascii=False, indent=2))
    (out / "goods.json").write_text(json.dumps(goods, ensure_ascii=False, indent=2))
    print(f"[ok] 已生成 {out}/users.json ({len(users)} 用户) / goods.json ({len(goods)} 商品)")


if __name__ == "__main__":
    main()