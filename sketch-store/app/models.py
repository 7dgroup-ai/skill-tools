"""模型层：纯函数式数据访问（配合 db.py 的 sqlite3，无需 ORM 依赖）。"""
import uuid

from .db import get_conn


def create_tables():
    from .db import init_db
    init_db()


# ---------- 用户 ----------
def get_user_by_username(username: str):
    with get_conn() as c:
        row = c.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        return dict(row) if row else None


def insert_user(username: str, password: str, nickname: str = None):
    with get_conn() as c:
        cur = c.execute(
            "INSERT INTO users (username, password, nickname) VALUES (?, ?, ?)",
            (username, password, nickname),
        )
        return cur.lastrowid


# ---------- 商品 ----------
def count_goods():
    with get_conn() as c:
        return c.execute("SELECT COUNT(*) AS n FROM goods").fetchone()["n"]


def list_goods(page: int = 1, size: int = 20):
    """真实分页；深分页(page*size 很大)无索引，模拟全表扫描。"""
    with get_conn() as c:
        rows = c.execute(
            "SELECT * FROM goods ORDER BY id LIMIT ? OFFSET ?",
            (size, (page - 1) * size),
        ).fetchall()
        return [dict(r) for r in rows]


def get_goods(goods_id: int):
    with get_conn() as c:
        row = c.execute("SELECT * FROM goods WHERE id = ?", (goods_id,)).fetchone()
        return dict(row) if row else None


def insert_goods(name, category, price, stock):
    with get_conn() as c:
        return c.execute(
            "INSERT INTO goods (name, category, price, stock) VALUES (?, ?, ?, ?)",
            (name, category, price, stock),
        ).lastrowid


# ---------- 购物车 ----------
def add_cart(user_id: int, goods_id: int, num: int):
    with get_conn() as c:
        row = c.execute(
            "SELECT * FROM carts WHERE user_id = ? AND goods_id = ?", (user_id, goods_id)
        ).fetchone()
        if row:
            c.execute(
                "UPDATE carts SET num = num + ? WHERE id = ?", (num, row["id"])
            )
            return row["id"]
        return c.execute(
            "INSERT INTO carts (user_id, goods_id, num) VALUES (?, ?, ?)",
            (user_id, goods_id, num),
        ).lastrowid


def list_cart(user_id: int):
    with get_conn() as c:
        rows = c.execute(
            """SELECT c.id AS cart_id, g.id AS goods_id, g.name, g.price,
                      c.num, ROUND(g.price * c.num, 2) AS subtotal
               FROM carts c JOIN goods g ON c.goods_id = g.id
               WHERE c.user_id = ?""",
            (user_id,),
        ).fetchall()
        items = [dict(r) for r in rows]
        total = round(sum(i["subtotal"] for i in items), 2)
        return items, total


# ---------- 订单 ----------
def create_order(user_id: int, order_id: str = None):
    order_id = order_id or f"ORD{uuid.uuid4().hex[:12].upper()}"
    items, total = list_cart(user_id)
    if not items:
        return None
    with get_conn() as c:
        c.execute(
            "INSERT INTO orders (order_id, user_id, total_amount, status) VALUES (?, ?, ?, 'PREVIEW')",
            (order_id, user_id, total),
        )
        for it in items:
            c.execute(
                "INSERT INTO order_items (order_id, goods_id, goods_name, price, num) VALUES (?, ?, ?, ?, ?)",
                (order_id, it["goods_id"], it["name"], it["price"], it["num"]),
            )
        c.execute("DELETE FROM carts WHERE user_id = ?", (user_id,))
    return {"order_id": order_id, "total_amount": total, "items": items, "status": "PREVIEW"}


def get_order(order_id: str, user_id: int):
    with get_conn() as c:
        o = c.execute(
            "SELECT * FROM orders WHERE order_id = ? AND user_id = ?", (order_id, user_id)
        ).fetchone()
        if not o:
            return None
        items = [
            dict(r)
            for r in c.execute(
                "SELECT goods_id, goods_name, price, num FROM order_items WHERE order_id = ?",
                (order_id,),
            )
        ]
        return {"order_id": o["order_id"], "total_amount": o["total_amount"], "status": o["status"], "items": items}


def pay_order(order_id: str, user_id: int, pay_type: str, request_id: str):
    with get_conn() as c:
        o = c.execute(
            "SELECT * FROM orders WHERE order_id = ? AND user_id = ?", (order_id, user_id)
        ).fetchone()
        if not o:
            return {"ok": False, "msg": "订单不存在"}
        # 幂等：同一 request_id 重复支付不重复处理
        dup = c.execute("SELECT 1 FROM payments WHERE request_id = ?", (request_id,)).fetchone()
        if dup:
            return {"ok": True, "msg": "幂等已处理", "order_id": order_id}
        if o["status"] == "PAID":
            return {"ok": True, "msg": "已支付", "order_id": order_id}
        c.execute("UPDATE orders SET status = 'PAID' WHERE order_id = ?", (order_id,))
        c.execute(
            "INSERT INTO payments (order_id, pay_type, request_id, status) VALUES (?, ?, ?, 'SUCCESS')",
            (order_id, pay_type, request_id),
        )
    return {"ok": True, "order_id": order_id}