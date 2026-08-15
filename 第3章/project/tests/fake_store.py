"""fake sketch-store：测试用内存版被测应用（业务语义对齐《被测应用设计手稿》8 步链路）。

以纯同步 handler + httpx.MockTransport 提供，避免 ASGI 异步传输在同步
HttpClient 下的兼容问题。业务语义与 FastAPI 版（mocks/app.py）保持一致。
"""

from __future__ import annotations

import json
import time
import uuid
from typing import Any

import httpx

# 内存态：token -> {"user": str, "cart": list, "order_id": str|None}
_SESSIONS: dict[str, dict] = {}
_ORDERS: dict[str, dict] = {}
USERS = {"u_1001": "pass_1001", "u_1002": "pass_1002"}
GOODS = {f"g_{2001 + i}": {"price": 19.9} for i in range(5)}


def _dispatch(method: str, path: str, params: dict, body: dict,
              token: str) -> tuple[int, dict]:
    """路由分发：返回 (status, payload)。"""
    if path == "/api/goods/list":
        page = int(params.get("page", 1))
        if page <= 0:
            return 200, {"code": -1, "msg": "非法页码"}
        items = [{"id": gid, "price": g["price"]} for gid, g in GOODS.items()]
        return 200, {"code": 0, "data": {"total": len(items), "items": items}}

    if path == "/api/login":
        username, password = body.get("username"), body.get("password")
        if USERS.get(username) != password:
            return 200, {"code": 1001, "msg": "用户名或密码错误"}
        tok = uuid.uuid4().hex
        _SESSIONS[tok] = {"user": username, "cart": [], "order_id": None}
        return 200, {"code": 0, "data": {"token": tok, "expires_in": 3600}}

    if token not in _SESSIONS:
        return 401, {"code": -1, "msg": "未登录或 token 失效"}
    sess = _SESSIONS[token]

    if path == "/api/cart/add":
        goods_id, num = body.get("goods_id"), body.get("num", 1)
        if goods_id not in GOODS:
            return 200, {"code": 2002, "msg": "商品不存在"}
        if not isinstance(num, int) or num <= 0:
            return 200, {"code": 2003, "msg": "数量非法"}
        sess["cart"].append({"goods_id": goods_id, "num": num})
        return 200, {"code": 0, "data": {"cart_size": len(sess["cart"])}}

    if path == "/api/cart/list":
        return 200, {"code": 0, "data": {"items": sess["cart"],
                                         "total": sum(i["num"] for i in sess["cart"])}}

    if path == "/api/order/preview":
        if not sess["cart"]:
            return 200, {"code": 3001, "msg": "购物车为空"}
        order_id = f"order-{time.time_ns()}"
        sess["order_id"] = order_id
        return 200, {"code": 0, "data": {"order_id": order_id, "amount": 19.9}}

    if path == "/api/order/pay":
        if body.get("order_id") != sess.get("order_id"):
            return 200, {"code": 3002, "msg": "订单号不匹配"}
        _ORDERS[sess["order_id"]] = {"user": sess["user"], "status": "PAID"}
        return 200, {"code": 0, "data": {"status": "PAID"}}

    if path.startswith("/api/order/"):
        order_id = path.rsplit("/", 1)[-1]
        order = _ORDERS.get(order_id)
        if not order:
            return 200, {"code": 3003, "msg": "订单不存在"}
        return 200, {"code": 0, "data": {"order_id": order_id, "status": order["status"]}}

    if path == "/health":
        return 200, {"code": 0, "msg": "ok"}

    return 404, {"code": -1, "msg": "not found"}


def make_transport() -> httpx.MockTransport:
    """构造 httpx.MockTransport，供 HttpClient(transport=...) 使用。"""

    def handler(request: httpx.Request) -> httpx.Response:
        params = dict(request.url.params)
        try:
            raw = request.read().decode("utf-8")
            body: dict[str, Any] = json.loads(raw) if raw else {}
        except Exception:
            body = {}
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        status, payload = _dispatch(request.method, request.url.path, params, body, token)
        return httpx.Response(status, json=payload)

    return httpx.MockTransport(handler)
