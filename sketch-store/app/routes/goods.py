from fastapi import APIRouter, Depends, Header, Query, Request

from .. import latency_sim, metrics
from .. import models

router = APIRouter(prefix="/api/goods", tags=["goods"])


@router.get("/list")
def goods_list(
    request: Request,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=200),
):
    """商品列表（公开接口）。cache_path 开关命中缓存；latency_sim 注入慢查询。"""
    latency_sim.maybe_sleep()  # latency_sim 开 -> 全量注入延迟

    def producer():
        rows = models.list_goods(page, size)
        return {"page": page, "size": size, "total": models.count_goods(), "list": rows}

    data = latency_sim.goods_cache(page, size, producer)
    metrics.inc_business("goods_list")
    return {"code": 0, "data": data}