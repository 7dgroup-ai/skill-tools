"""瓶颈注入开关（全书瓶颈定位/故障注入章节的可控素材）：
- latency_sim: 慢查询开关，打开后商品列表深分页与支付接口注入人为延迟
- cache_path:  缓存开关，打开后商品列表走内存缓存，关闭则每次都查库
- sql_injection: 安全测试演示用：登录接口是否走有 SQL 注入风险的拼接查询
"""
import time

_state = {
    "latency_sim": False,
    "cache_path": False,
    "sql_injection": True,
}

_latency_ms = 800  # latency_sim 打开时注入的延迟
_cache = {"goods_page": None, "page": 0, "size": 0}


def get(name):
    return _state.get(name, False)


def set(name, value):
    if name in _state:
        _state[name] = bool(value)
    return _state.get(name)


def set_latency_ms(ms):
    global _latency_ms
    _latency_ms = max(0, int(ms))


def get_latency_ms():
    return _latency_ms


def maybe_sleep():
    """latency_sim 打开时注入延迟（模拟慢 DB 查询）。"""
    if _state["latency_sim"]:
        time.sleep(_latency_ms / 1000.0)


def goods_cache(page, size, producer):
    """cache_path 打开时命中内存缓存，关闭时每次走 DB。"""
    if _state["cache_path"]:
        if _cache["goods_page"] and _cache["page"] == page and _cache["size"] == size:
            return _cache["goods_page"]
        data = producer()
        _cache.update({"goods_page": data, "page": page, "size": size})
        return data
    _cache.update({"goods_page": None, "page": 0, "size": 0})
    return producer()


def switch_summary():
    return dict(_state, latency_ms=_latency_ms)