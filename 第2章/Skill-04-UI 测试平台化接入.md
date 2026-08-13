# Skill-04-UI 测试平台化接入

> **能力名称**：UI 测试平台化接入（FastAPI + APScheduler 用例调度 + Allure 报告聚合 + 重跑机制 + 设备农场接入 + 减配方案）
> **生命周期阶段**：构建/度量
> **资产来源**：第 2 章 §2.6 测试平台自建；project/platform 工程；scripts 统一入口
> **文档版本**：v1.0 | 维护者：李文 | 更新日期：2026-08-06

---

## 0. 一句话定位

当用例量上规模后，需要一个平台管"用例、调度、报告、重跑"——本 Skill 给最小可用的自建方案，不追求商业化平台的功能，先闭环；提供减配方案（单机 + 简单队列）与全配演进路径。

---

## 1. 触发场景（何时调用）

- [ ] UI 自动化用例数 > 50，人工跑批、人工看报告已成瓶颈，需集中调度、聚合报告、失败自动重跑
- [ ] 多端（Web/App）用例需统一调度、统一报告聚合、统一触发性能测试
- [ ] 需要设备农场管理：多设备并发、空闲分配、执行完归还、心跳监控
- [ ] 团队无预算/人力上商业平台（Testin/云测/自研大平台），需最小可用自建方案，**先闭环、再演进**

> 不需要此 Skill 的场景：用例 < 20、仅本地跑、仅 CI 跨批、无设备农场需求、预算充足可直接上商业平台。

---

## 2. 输入契约（Input Contract）

| 项 | 必备/可选 | 说明 |
|---|---|---|
| 已有 UI 自动化工程 | 必备 | Web (Skill-01) / App (Skill-02) / 跨平台 (Skill-03) 已能独立跑通 |
| 用例标识体系 | 必备 | 每个用例有唯一 `case_id`，可通过 CLI 单独触发（如 `pytest -k buy_flow`） |
| Allure 报告输出 | 必备 | 用例执行后产出 `allure-results/` 目录 |
| Python 环境 | 必备 | Python 3.10+，可安装 FastAPI/APScheduler/Allure |
| 设备池（可选） | 可选 | 多 Android 设备 + `device.py:list_devices()` 可枚举 |

**入口检查清单**：
- [ ] `pytest tests/ --junitxml=reports/junit.xml --alluredir=reports/allure-results` 单机跑通
- [ ] `allure generate reports/allure-results -o reports/allure-report` 生成静态报告
- [ ] `python -m uvicorn platform.scheduler:app --port 8000` 平台启动无报错
- [ ] 明确"重跑判定规则"（如 timeout/element not found 重跑 2 次）

---

## 3. 工具链（Toolchain）

| 工具 | 版本 | 角色 | 备选 |
|---|---|---|---|
| FastAPI | ≥0.110 | Web API 框架（用例管理/触发/查询） | Flask / Starlette |
| APScheduler | ≥3.10 | 后台定时调度（cron/interval） | Celery Beat |
| Allure | ≥2.13 | 报告生成/聚合/静态站 | ReportPortal |
| uiautomator2 | ≥3.0 | 设备管理/连接心跳 | — |
| requests / httpx | ≥0.27 | 跨服务调用（触发性能/回调） | — |
| cron / systemd | — | 减配方案：单机定时任务 | Jenkins / GitLab CI |

**选型决策树**：
1. 团队无运维能力、追求极简 → **减配方案**：单机 + cron + 失败重跑脚本 + Allure 静态报告
2. 需要 Web 看板、多用户、多项目、设备农场 → **全配方案**：FastAPI + APScheduler + 设备池 + Allure 静态站
3. 已有 Jenkins/GitLab CI、只缺报告聚合 → 直接接 CI，复用现有调度，**仅补 Allure 聚合**

> 演进路径：减配（单机 cron）→ 全配（FastAPI 调度+设备池）→ 商业化（Testin/云测/自研平台）

---

## 4. 执行步骤

### 4.1 减配方案（单机 + 简单队列，立即可用）

> **不引入平台也可以闭环**：单机 + cron/CI 定时跑用例 + 失败重跑脚本 + Allure 报告，即"减配平台"。待规模扩大后再引入 FastAPI 调度与设备农场。

```bash
# 1) 失败重跑脚本（scripts/rerun.py）
#!/usr/bin/env python3
import subprocess, sys, json

def run_with_retry(cmd, max_retry=2, flaky_hints=("timeout", "element not found")):
    for attempt in range(1, max_retry + 1):
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if r.returncode == 0:
            return True
        if any(h in r.stderr for h in flaky_hints):
            print(f"[RETRY {attempt}/{max_retry}] {cmd}")
            continue
        return False
    return False

if __name__ == "__main__":
    ok = run_with_retry("pytest project/web/tests -v --junitxml=reports/junit.xml")
    sys.exit(0 if ok else 1)
```

```bash
# 2) crontab 定时跑（每天 02:00）
# crontab -e
0 2 * * * /bin/bash -lc "cd /path/to/project && bash scripts/run_web_tests.sh >> logs/web_$(date +\%F).log 2>&1"

# 3) Allure 报告聚合（定时或手动）
allure generate reports/allure-results -o reports/allure-report --clean
# 暴露 reports/allure-report 目录给 Nginx 静态站
```

### 4.2 全配方案（FastAPI + APScheduler + 设备池 + Allure 看板）

```
project/platform/
├── scheduler.py          # FastAPI + APScheduler：用例管理、定时触发、手动触发
├── rerunner.py           # 失败重跑队列：真失败判定 → 排队重跑 → 结果回写
├── models.py             # 数据模型（用例、执行记录、设备、报告）
└── requirements.txt      # fastapi uvicorn apscheduler requests uiautomator2
```

**核心代码片段**：

```python
# scheduler.py —— FastAPI + APScheduler
from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI

app = FastAPI()
scheduler = BackgroundScheduler()

def _run_case(case_id: str) -> None:
    # 调用用例执行器（对接 Playwright / UiAutomator2 用例），执行后写报告
    print(f"run case: {case_id}")
    # 实际：subprocess.run(["pytest", f"-k {case_id}", "--junitxml=...", "--alluredir=..."])

@app.on_event("startup")
def _start():
    scheduler.add_job(lambda: _run_case("buy_flow"), "cron", hour=2, minute=0)  # 每天 02:00
    scheduler.start()

@app.post("/cases/{case_id}/run")
def run_now(case_id: str):
    _run_case(case_id)
    return {"ok": True, "case_id": case_id}

# GET /cases          # 列出所有用例
# GET /cases/{id}     # 查询用例详情
# GET /reports/{id}   # 查询执行记录
```

```python
# rerunner.py —— 失败重跑（先真失败判定，再排队重跑）
class Rerunner:
    def __init__(self, max_retry: int = 2,
                 flaky_hint: tuple = ("timeout", "element not found")):
        self._max_retry = max_retry
        self._flaky = flaky_hint

    def rerun(self, failed_case, collector):
        for attempt in range(1, self._max_retry + 1):
            result = collector.run(failed_case)      # 重新执行
            if result.passed:
                return {"case": failed_case, "status": "passed_on_retry", "attempt": attempt}
        return {"case": failed_case, "status": "failed", "attempt": self._max_retry}
```

**设备农场接入**：
```python
# device.py 扩展为设备池
def acquire_device() -> str:
    """从池中分配空闲设备，返回 serial；无空闲则阻塞/报错。"""
    for serial in list_devices():
        if is_idle(serial):
            mark_busy(serial)
            return serial
    raise RuntimeError("设备池无空闲设备")

def release_device(serial: str) -> None:
    mark_idle(serial)
```
> 平台从池中分配空闲设备执行用例，执行完归还（对接 §2.2.3 `device.py:list_devices()`）。

### 4.3 Allure 报告聚合 + Web 看板

```bash
# 1) 用例执行后写 Allure 结果目录
pytest tests/ --alluredir=reports/allure-results

# 2) 平台生成聚合报告
allure generate reports/allure-results -o reports/allure-report --clean

# 3) 暴露静态目录（Nginx / FastAPI StaticFiles）
# 看板展示：通过率 / 失败截图 / 执行耗时 / 历史趋势
```

### 4.4 统一造数 + 触发性能入口（scripts/）

```bash
# scripts/seed_data.py — 统一造数入口（Web/App 双模）
# python scripts/seed_data.py --web --count 10
# python scripts/seed_data.py --app --count 10

# scripts/trigger_perf.py — 造数完成后触发性能测试（第 5 章）
import requests, sys
def trigger_perf(data_file="data/seed_orders.csv"):
    # 示例：调用 GitLab CI Pipeline API / Jenkins / 性能平台
    print(f"[MOCK] 触发性能测试，数据文件: {data_file}")
    return True

# scripts/run_web_tests.sh / run_app_tests.sh — 一键跑通
# bash scripts/run_web_tests.sh
# bash scripts/run_app_tests.sh
```

### 4.5 一键全链路演示

```bash
# Web 全链路：功能验证 → 造数 → 触发性能
bash scripts/run_web_tests.sh && python scripts/seed_data.py --web --count 10 && python scripts/trigger_perf.py

# App 全链路（需真机/模拟器）
bash scripts/run_app_tests.sh && python scripts/seed_data.py --app --count 10 && python scripts/trigger_perf.py
```

---

## 5. 输出契约（Output Contract）

| 产物 | 说明 |
|---|---|
| `project/platform/` | 调度服务（scheduler.py）、重跑服务（rerunner.py）、设备池扩展 |
| `scripts/` | 统一造数入口、触发性能、一键跑通 Shell |
| 调度 API | `POST /cases/{id}/run` 手动触发、定时 Cron 自动触发 |
| 报告聚合 | Allure 静态站（通过率/截图/耗时/趋势），Nginx/FastAPI 暴露 |
| 重跑能力 | 真失败判定 → 入队 → 重跑 → 结果回写（最多 N 次，flaky hint 白名单） |
| 设备池 | `acquire_device()` / `release_device()` 可接入并发调度 |
| 触发性能 | `scripts/trigger_perf.py` 造数后自动触发下游性能测试 |

**验收前必须能当面演示**：
```bash
# 1) 减配：单机 cron + 重跑脚本 + Allure 报告
bash scripts/run_web_tests.sh
allure generate reports/allure-results -o reports/allure-report

# 2) 全配：启动平台 + 手动触发 + 查看看板
python -m uvicorn platform.scheduler:app --port 8000 &
curl -X POST http://127.0.0.1:8000/cases/buy_flow/run
# 浏览器打开 http://<IP>:8000/reports 查看聚合报告

# 3) 造数 → 触发性能全链路
bash scripts/run_web_tests.sh && python scripts/seed_data.py --web --count 10 && python scripts/trigger_perf.py
```

---

## 6. 验收清单（Acceptance Checklist）

- [ ] 单机减配方案跑通：cron 定时跑用例、失败重跑脚本生效、Allure 报告可生成可查看
- [ ] 全配平台启动无报错：`uvicorn platform.scheduler:app --port 8000`，Swagger 文档 `/docs` 可访问
- [ ] 手动触发用例：`POST /cases/buy_flow/run` 返回 `{"ok": true}`，后台异步执行并写报告
- [ ] 定时调度生效：每天 02:00 自动跑 `buy_flow`，执行记录可查询
- [ ] 失败重跑：模拟 timeout/element not found，重跑 2 次后回写 `passed_on_retry` / `failed`
- [ ] Allure 报告聚合：多次执行结果合并生成静态站，看板展示通过率/截图/耗时/趋势
- [ ] 设备农场：`device.py:list_devices()` 扩展为 `acquire/release`，并发调度无冲突
- [ ] 造数 → 触发性能：`bash run_web_tests.sh && python seed_data.py --web --count 10 && python trigger_perf.py` 一键跑通

---

## 7. 常见坑点（Pitfalls）

| 现象 | 原因 | 排查 |
|---|---|---|
| APScheduler 任务不执行 | 时区/进程守护/启动顺序 | `scheduler.start()` 放在 `@app.on_event("startup")`；生产用 systemd 守护 |
| 重跑无限循环 | flaky hint 写错 / 真失败也被重跑 | `flaky_hint` 仅放 `("timeout", "element not found")`；真业务失败不重跑 |
| Allure 报告不更新 | 生成目录未清理 / 路径错 | `allure generate ... --clean`；确认 `allure-results` 目录权限 |
| 设备并发冲突 | 多任务抢同一设备 | `acquire_device()` 加锁/原子操作；无空闲时阻塞或快速失败 |
| 触发性能失败 | 网络不通 / Token 过期 | `trigger_perf.py` 加重试 + 告警；Token 统一由配置中心下发 |

---

## 8. 能力等级（L1-L4）

| 等级 | 表现 |
|---|---|
| L1 | 能跑通减配方案：cron + 重跑脚本 + Allure 报告；理解平台三大能力（调度/报告/重跑） |
| L2 | 能部署全配平台：FastAPI + APScheduler + Allure 看板；编写定时/手动触发 API；接入重跑 |
| L3 | 能设计设备池并发模型、实现 `acquire/release`、对接 Skill-02 设备管理、扩展多项目隔离 |
| L4 | 能搭建企业级测试平台：多租户、RBAC、用例市场、报告聚合看板、与 CI/CD/性能平台/监控全打通、资产治理（Skill-29） |

---

## 9. 附：最小可运行示例（减配方案）

```bash
# 1) 单机跑 Web 用例 + 失败重跑
bash scripts/run_web_tests.sh   # 内含 pytest + junitxml + 失败重跑逻辑

# 2) 生成 Allure 报告
allure generate reports/allure-results -o reports/allure-report --clean
# 用 Nginx 暴露 reports/allure-report 即可看看板

# 3) 造数 + 触发性能
python scripts/seed_data.py --web --count 10 && python scripts/trigger_perf.py
```

---

*参考：第 2 章 §2.6 测试平台自建、project/platform/ 工程、scripts/ 统一入口、Skill-16 多协议性能脚本构建（同模板）*