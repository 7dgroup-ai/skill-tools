"""最小 Demo 前端：UI 自动化的真实被测对象（登录 → 商品 → 加购 → 结算 → 建单）。

业务语义对齐《被测应用设计手稿》8 步链路中的前端部分。
sketch-store 是 API 优先应用（无 UI），本 Demo 前端作为其 UI 层替身，
供 Playwright / UiAutomator2 等 UI 自动化驱动。

启动：uvicorn demo_app.main:app --port 8080
"""

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.responses import FileResponse, JSONResponse

app = FastAPI(title="demo-ui-front")

_BASE = Path(__file__).parent
_SESSIONS: dict[str, dict] = {}          # sid -> {"user": str, "cart": list}
_USERS = {"u_1001": "pass_1001", "seed_user_0": "pass_0000",
          "seed_user_1": "pass_0000", "seed_user_2": "pass_0000"}
_GOODS = [{"id": "g_2001", "name": "商品A", "price": 19.9},
          {"id": "g_2002", "name": "商品B", "price": 29.9}]
_ORDER_COUNT = {"n": 0}


def _session(req: Request) -> dict | None:
    sid = req.cookies.get("demo_sid")
    return _SESSIONS.get(sid) if sid else None


@app.get("/")
def index():
    return FileResponse(_BASE / "index.html")


@app.get("/health")
def health():
    return {"code": 0, "msg": "ok"}


@app.post("/api/login")
async def login(req: Request, resp: Response):
    body = json.loads(await req.body())
    username, password = body.get("username"), body.get("password")
    if _USERS.get(username) != password:
        return JSONResponse({"code": 1001, "msg": "用户名或密码错误"}, status_code=200)
    sid = uuid.uuid4().hex
    _SESSIONS[sid] = {"user": username, "cart": []}
    resp.set_cookie("demo_sid", sid)
    return {"code": 0, "data": {"user": username}}


@app.get("/api/goods")
def goods():
    return {"code": 0, "data": {"items": _GOODS}}


@app.post("/api/cart/add")
async def cart_add(req: Request):
    sess = _session(req)
    if not sess:
        return JSONResponse({"code": -1, "msg": "请先登录"}, status_code=401)
    body = json.loads(await req.body())
    goods_id, num = body.get("goods_id"), body.get("num", 1)
    if goods_id not in {g["id"] for g in _GOODS}:
        return {"code": 2002, "msg": "商品不存在"}
    sess["cart"].append({"goods_id": goods_id, "num": num})
    return {"code": 0, "data": {"cart_size": len(sess["cart"])}}


@app.get("/api/cart")
def cart(req: Request):
    sess = _session(req)
    if not sess:
        return JSONResponse({"code": -1, "msg": "请先登录"}, status_code=401)
    return {"code": 0, "data": {"items": sess["cart"],
                                "total": sum(i["num"] for i in sess["cart"])}}


@app.post("/api/checkout")
async def checkout(req: Request):
    sess = _session(req)
    if not sess:
        return JSONResponse({"code": -1, "msg": "请先登录"}, status_code=401)
    if not sess["cart"]:
        return {"code": 3001, "msg": "购物车为空"}
    order_id = f"order-{time.time_ns()}"
    _ORDER_COUNT["n"] += 1
    sess["cart"] = []
    return {"code": 0, "data": {"order_id": order_id}}


@app.get("/api/orders/count")
def orders_count():
    return {"code": 0, "data": {"count": _ORDER_COUNT["n"]}}
