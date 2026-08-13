"""测试平台自建（Skill-04）[可选]：FastAPI + APScheduler 用例调度。

依赖：pip install fastapi uvicorn apscheduler
启动：uvicorn platform.scheduler:app --port 9000
"""

from __future__ import annotations

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI

app = FastAPI(title="ui-platform")
scheduler = BackgroundScheduler()


def _run_case(case_id: str) -> None:
    # 对接用例执行器：Playwright / UiAutomator2 用例，执行后写 Allure 结果
    print(f"[platform] run case: {case_id}")


@app.on_event("startup")
def _start():
    scheduler.add_job(lambda: _run_case("buy_flow"), "cron", hour=2, minute=0)
    scheduler.add_job(lambda: _run_case("seed_daily"), "cron", hour=4, minute=0)
    scheduler.start()


@app.on_event("shutdown")
def _stop():
    scheduler.shutdown()


@app.post("/cases/{case_id}/run")
def run_now(case_id: str):
    _run_case(case_id)
    return {"ok": True, "case_id": case_id}


@app.get("/health")
def health():
    return {"ok": True}
