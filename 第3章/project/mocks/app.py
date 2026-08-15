"""Python 内嵌 Mock 服务：下游隔离 + 异常注入。

启动：
    uvicorn mocks.app:app --port 9100
用途：
    - 隔离不可控的外部依赖（支付/短信/推送）
    - 注入 fail_rate（失败率）、delay_ms（超时），验证被测方降级/重试
"""

from __future__ import annotations

import time
from typing import Optional

from fastapi import FastAPI, Response

app = FastAPI(title="api-test-stack Mock Server")


@app.get("/health")
def health():
    return {"code": 0, "msg": "ok"}


@app.post("/pay")
def pay(resp: Response, fail_rate: float = 0.0, delay_ms: int = 0):
    """支付 Mock：fail_rate 注入失败、delay_ms 注入超时。"""
    if delay_ms:
        time.sleep(delay_ms / 1000)
    if fail_rate > 0 and (hash(str(time.time_ns())) % 100) / 100 < fail_rate:
        resp.status_code = 503
        return {"code": -1, "msg": "payment provider unavailable"}
    return {"code": 0, "transaction_id": f"tx-{time.time_ns()}"}


@app.post("/sms/send")
def sms(resp: Response, fail: Optional[bool] = False):
    if fail:
        resp.status_code = 500
        return {"code": -1, "msg": "sms provider error"}
    return {"code": 0, "msg_id": f"sms-{time.time_ns()}"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("mocks.app:app", host="127.0.0.1", port=9100, reload=False)
