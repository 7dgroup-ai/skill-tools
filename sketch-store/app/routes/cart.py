from fastapi import APIRouter, Depends, Header, Request

from .. import latency_sim, metrics
from .. import models
from .deps import require_user, get_auth_token

router = APIRouter(prefix="/api/cart", tags=["cart"])


@router.post("/add")
def cart_add(
    request: Request,
    body: dict,
    _user=Depends(require_user),
):
    goods_id = body.get("goods_id")
    num = int(body.get("num", 1))
    if not goods_id or num < 1:
        return {"code": 1, "msg": "goods_id/num 非法"}
    g = models.get_goods(goods_id)
    if not g:
        return {"code": 1, "msg": "商品不存在"}
    if g["stock"] < num:
        return {"code": 1, "msg": "库存不足"}
    models.add_cart(_user["uid"], goods_id, num)
    metrics.inc_business("cart_add")
    return {"code": 0, "data": {"goods_id": goods_id, "num": num}}


@router.get("/list")
def cart_list(request: Request, _user=Depends(require_user)):
    items, total = models.list_cart(_user["uid"])
    metrics.inc_business("cart_list")
    return {"code": 0, "data": {"items": items, "total": total}}