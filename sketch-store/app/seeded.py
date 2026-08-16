"""铺底数据：1000 商品 + 500 用户。幂等：已有数据则跳过。
执行：python -m app.seeded 或 make seed 调用 scripts/seed.py
"""
import hashlib

from . import models
from .db import init_db

GOODS_COUNT = 1000
USER_COUNT = 500

_CATEGORIES = ["数码", "服饰", "家居", "食品", "美妆", "图书", "运动", "母婴"]


def _pwd(p):
    return hashlib.sha256(p.encode()).hexdigest()


def seed(scale="local"):
    """scale=local -> 1000 商品/500 用户；scale=prod -> 放大 100 倍（对齐设计手稿 DAU 档位）。"""
    init_db()
    goods_target = GOODS_COUNT if scale == "local" else GOODS_COUNT * 100
    user_target = USER_COUNT if scale == "local" else USER_COUNT * 100

    if models.count_goods() >= goods_target:
        print(f"[seed] goods 已就绪: {models.count_goods()} (>= {goods_target})")
    else:
        for i in range(1, goods_target + 1):
            cat = _CATEGORIES[i % len(_CATEGORIES)]
            models.insert_goods(
                name=f"商品{i:05d}",
                category=cat,
                price=round((i % 1000) + 0.99, 2),
                stock=(i % 500) + 100,
            )
        print(f"[seed] 商品铺底完成: {goods_target}")

    # 用户
    with models.get_conn() as c:
        n = c.execute("SELECT COUNT(*) AS n FROM users").fetchone()["n"]
    if n >= user_target:
        print(f"[seed] users 已就绪: {n} (>= {user_target})")
    else:
        for i in range(1, user_target + 1):
            models.insert_user(
                username=f"user{i:05d}",
                password=_pwd(f"pass{i:05d}"),
                nickname=f"用户{i:05d}",
            )
        print(f"[seed] 用户铺底完成: {user_target}")

    print("[seed] 完成。默认账号示例: user00001 / pass00001")


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--scale", default="local", choices=["local", "prod"])
    args = ap.parse_args()
    seed(args.scale)