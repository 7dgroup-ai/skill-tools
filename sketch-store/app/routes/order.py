import time

from fastapi import APIRouter, Depends, Request

from .. import latency_sim, metrics
from .. import models
from .deps import require_user

router = APIRouter(prefix="/api/order", tags=["order"])


@router.post("/preview")
def order_preview(request: Request, body: dict = None, _user=Depends(require_user)):
    """由购物车生成预览单（返回 order_id 供关联）。"""
    result = models.create_order(_user["uid"])
    if not result:
        return {"code": 1, "msg": "购物车为空，先加购"}
    metrics.inc_business("order_preview")
    return {"code": 0, "data": result}


@router.post("/create")
def order_create(request: Request, body: dict = None, _user=Depends(require_user)):
    """正式建单（携带 preview 返回的 order_id）。"""
    order_id = (body or {}).get("order_id")
    if not order_id:
        return {"code": 1, "msg": "缺少 order_id（需先 preview）"}
    order = models.get_order(order_id, _user["uid"])
    if not order:
        return {"code": 1, "msg": "订单不存在"}
    if order["status"] == "PREVIEW":
        # 简化状态机：PREVIEW 直接转 CREATED
        with models.get_conn() as c:
            c.execute("UPDATE orders SET status='CREATED' WHERE order_id=?", (order_id,))
        order["status"] = "CREATED"
    metrics.inc_business("order_create")
    return {"code": 0, "data": order}


@router.post("/pay")
def order_pay(request: Request, body: dict = None, _user=Depends(require_user)):
    """支付：模拟支付 + 延时（latency_sim 打开时慢）。幂等靠 request_id。"""
    body = body or {}
    order_id = body.get("order_id")
    request_id = body.get("request_id") or f"pay-{_user['uid']}-{time.time()}"
    pay_type = body.get("pay_type", "mock")
    latency_sim.maybe_sleep()
    result = models.pay_order(order_id, _user["uid"], pay_type, request_id)
    if result["ok"]:
        metrics.inc_business("pay_success")
    return {"code": 0 if result["ok"] else 1, "msg": result.get("msg", ""), "data": result}


@router.get("/{order_id}")
def order_get(order_id: str, request: Request, _user=Depends(require_user)):
    """查单：断言校验落点。"""
    order = models.get_order(order_id, _user["uid"])
    if not order:
        return {"code": 1, "msg": "订单不存在"}
    metrics.inc_business("order_query")
    return {"code": 0, "data": order}