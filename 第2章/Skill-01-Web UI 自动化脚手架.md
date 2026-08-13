# Skill-01-Web UI 自动化脚手架

> **能力名称**：Web UI 自动化脚手架（Playwright / Cypress / Selenium 4.x 选型与 Pytest + Allure + Fixture 体系搭建）
> **生命周期阶段**：准备/构建
> **资产来源**：第 2 章 §2.1 Web 自动化；project/web 工程（Playwright + Pytest + Allure + PageObject + CI）
> **文档版本**：v1.0 | 维护者：李文 | 更新日期：2026-08-06

---

## 0. 一句话定位

建立"可维护、可上 CI、可驱动下游"的 Web UI 自动化工程脚手架：选型 → 脚手架 → PageObject → CI 集成 → 实测验证，形成"功能验证 → 造数 → 触发性能"的流水线起点。

---

## 1. 触发场景（何时调用）

- [ ] 新项目需要建立 Web UI 自动化，需在 Playwright / Cypress / Selenium 4.x 中三选一
- [ ] 现有 UI 脚本无结构（线性脚本），维护成本高，需引入 PageObject / Screenplay 分层
- [ ] 需将 UI 自动化接入 CI（GitHub Actions / GitLab CI），失败自动截图+录视频+Allure 报告
- [ ] UI 自动化需产出铺底数据，驱动下游非功能测试（接口/性能/安全）

> 不需要此 Skill 的场景：仅做接口功能验证（用 Skill-05 即可）、无前端的纯后端系统、仅做性能压测（用 Skill-16/17/18）。

---

## 2. 输入契约（Input Contract）

| 项 | 必备/可选 | 说明 |
|---|---|---|
| 被测前端地址 | 必备 | base URL（如 `http://127.0.0.1:8080`），需可直接访问 |
| 业务页面结构 | 必备 | 登录/商品/购物车/结算等关键页面的 HTML 结构与定位特征 |
| 测试账号与数据 | 必备 | 至少 1 个可登录账号（如 `u_1001/pass_1001`），商品列表已就绪 |
| Python 环境 | 必备 | Python 3.10+，可安装 Playwright 及依赖 |
| CI 运行器 | 可选 | GitHub Actions / GitLab CI Runner，需可安装浏览器二进制 |

**入口检查清单**：
- [ ] 被测前端 `/health` 返回 `{"code":0,"msg":"ok"}`
- [ ] 登录页存在 `placeholder="用户名"`、`placeholder="密码"`、`button:has-text("登录")` 等语义定位特征
- [ ] 明确"登录成功"的断言口径（页面跳转 / Cookie / 页面文本包含"登录成功"）

---

## 3. 工具链（Toolchain）

| 工具 | 版本 | 角色 | 备选 |
|---|---|---|---|
| Playwright | ≥1.42 | 核心驱动（首选） | Cypress / Selenium 4.x |
| Pytest | ≥8.0 | 测试运行器 | — |
| pytest-playwright | ≥0.5 | Pytest 插件 | — |
| Allure-pytest | ≥2.13 | 报告生成 | — |
| FastAPI + Uvicorn | ≥0.110 / ≥0.29 | Demo 前端服务 | — |
| GitHub Actions / GitLab CI | — | CI 跑批 | Jenkins |

**选型决策树**：
1. 需跨浏览器（Chromium/Firefox/WebKit）+ 语义定位（`get_by_role/text/placeholder`） → **Playwright**
2. 团队已有 Cypress 生态、前端强、需实时重载 → **Cypress**
3. 遗留 Java/多语言栈、需 Selenium Grid 分布式执行 → **Selenium 4.x**
4. 仅需 Android/iOS 原生 → 见 Skill-02/03

> 炼手建议：先跑通 `demo_app`（`uvicorn demo_app.main:app --port 8080`），再用 Playwright 录一遍"登录→加购→结算"，确认语义定位可用后再上脚手架。

---

## 4. 执行步骤（使用 Playwright + Pytest 为主线）

### 4.1 环境准备与脚手架搭建

```bash
# 1) 进入 Web 工程目录
cd project/web

# 2) 安装依赖
pip install -r requirements.txt
# playwright>=1.42 pytest>=8.0 pytest-playwright>=0.5 fastapi>=0.110 uvicorn>=0.29 httpx>=0.27

# 3) 安装浏览器二进制（首次必跑，需联网）
playwright install chromium  # 或 playwright install --with-deps chromium
```

### 4.2 核心脚手架代码（`project/web/` 目录结构）

```
project/web/
├── conftest.py              # 浏览器 fixture：session 级 browser + function 级 page
├── demo_app/                # 最小 Demo 前端（FastAPI + 静态页）
│   ├── main.py              # 登录/商品/加购/结算/建单 接口 + / 页面
│   └── index.html           # 登录表单 + 商品卡 + 购物车
├── pages/                   # PageObject 层
│   ├── login_page.py        # 用户名/密码/登录按钮/错误提示
│   └── shop_page.py         # 商品卡/加入购物车/结算/订单号
├── tests/
│   ├── test_buy_flow.py     # 登录→加购→结算→建单（功能验证）
│   ├── test_seed_data.py    # UI 造数：循环建单 N 单（铺底数据生成）
│   └── test_demo_api.py     # Demo 前端接口单测（无浏览器也可跑）
└── pyproject.toml           # pytest 配置：testpaths=["tests"], pythonpath=["."]
```

**关键代码片段**：

```python
# conftest.py —— 浏览器 fixture（headless + 系统 Chrome 兼容）
import pytest
from playwright.sync_api import sync_playwright

BASE_URL = "http://127.0.0.1:8080"

@pytest.fixture(scope="session")
def browser():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, channel="chrome")  # 系统 Chrome 规避内置下载失败
        yield browser
        browser.close()

@pytest.fixture()
def page(browser, base_url=BASE_URL):
    ctx = browser.new_context(viewport={"width": 1280, "height": 720})
    pg = ctx.new_page()
    pg.goto(base_url)
    yield pg
    ctx.close()
```

```python
# pages/login_page.py —— 语义定位
from playwright.sync_api import Page

class LoginPage:
    def __init__(self, page: Page):
        self.page = page
        self.username = page.get_by_placeholder("用户名")
        self.password = page.get_by_placeholder("密码")
        self.submit = page.get_by_role("button", name="登录")
        self.error = page.locator(".error")

    def login(self, username: str, password: str) -> None:
        self.username.fill(username)
        self.password.fill(password)
        self.submit.click()

    def error_text(self) -> str:
        return self.error.inner_text()
```

### 4.3 页面对象演进：PageObject → Screenplay

| 阶段 | 结构 | 优点 | 适用规模 |
|---|---|---|---|
| **线性脚本** | 用例里直接 `page.click(...)` | 快 | <10 用例 |
| **PageObject** | 页面类收口元素与动作 | 复用、可维护 | 10-100 用例 |
| **Screenplay** | Actor + Task + Question 分层 | 面向行为、可组合 | >100 用例 / 多角色 |

**演进原则**：只在"动作需要被多用例复用 / 出现多角色"时演进到 Screenplay，避免过度设计。小团队 PageObject 足够。

### 4.4 CI 集成（GitHub Actions 片段）

```yaml
# .github/workflows/ui.yml
name: ui-tests
on: [push, pull_request]
jobs:
  ui:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: {python-version: '3.11'}
      - run: pip install -r project/web/requirements.txt
      - run: playwright install --with-deps chromium
      - run: python project/web/demo_app/main.py &   # 起被测前端
      - run: pytest project/web/tests --junitxml=reports/junit.xml
      - uses: actions/upload-artifact@v4
        with: {name: allure-report, path: reports/}
```

---

## 5. 输出契约（Output Contract）

| 产物 | 说明 |
|---|---|
| `project/web/` 工程目录 | 含脚手架、Demo 前端、PageObject、用例、CI 配置 |
| 运行证明 | 单线程跑通 + N 线程跑通（各 ≥1 份取样结果） |
| 测试报告 | Allure 报告（含截图/录视频/步骤/耗时），JUnit XML 供 CI 门禁 |
| 铺底数据 | `data/seed_orders.csv`（行数 = `count + 1` 表头） |
| 触发器 | `scripts/trigger_perf.py` 造数完成后触发性能测试（第 5 章） |

**验收前必须能当面演示**：
```bash
# 1) 启动被测前端
python -m uvicorn demo_app.main:app --port 8080 &
# 2) 运行全部 Web 用例（含无浏览器接口测 + 有浏览器功能验证 + 造数）
python -m pytest tests/ -v   # 9 passed (test_demo_api 6 + test_buy_flow 2 + test_seed_data 1)
# 3) 一键全链路
bash scripts/run_web_tests.sh && python scripts/seed_data.py --web --count 10 && python scripts/trigger_perf.py
```

---

## 6. 验收清单（Acceptance Checklist）

- [ ] 启动 `demo_app` 后，`pytest tests/test_demo_api.py` 通过（无浏览器）
- [ ] 安装 Playwright 后，`test_buy_flow.py` 跑通"登录 → 加购 → 结算 → 建单"
- [ ] 失败用例自动截图/录视频（`screenshot="only-on-failure"`），Allure 报告可正常查看
- [ ] `bash scripts/run_web_tests.sh` 一键跑通功能验证
- [ ] `python scripts/seed_data.py --web --count 10` 产出 10 单铺底数据，且 `data/seed_orders.csv` 存在且行数=11(含表头)
- [ ] CI 流水线跑通：GitHub Actions / GitLab CI 自动安装依赖、安装浏览器、启动被测前端、跑用例、上传 Allure 报告工件
- [ ] 无敏感信息（密码/内网地址/Token）被写入代码/配置，均通过环境变量或 fixture 注入

---

## 7. 常见坑点（Pitfalls）

| 现象 | 原因 | 排查 |
|---|---|---|
| 定位漂移 | CI 偶发 `element not found` | 统一用 `get_by_role/text/placeholder` 语义定位；禁用脆弱的 CSS/XPath |
| 等待不足 | 点击后立即断言失败 | 依赖 Playwright 自动等待；显式等待只用 `expect(locator).to_be_visible()` |
| 状态污染 | 用例间账号/购物车互串 | 每用例独立 `browser.new_context()`；造数用专属 `seed_user_{n}` |
| 并发冲突 | 多 worker 同账号下单报错 | `pytest-xdist` + 数据池 Provider 分配唯一账号（见 §2.4.2） |
| 内置 Chromium 下载失败 | 网络拦截/无法访问微软 CDN | `p.chromium.launch(channel="chrome")` 改用系统 Chrome；或配置 `PLAYWRIGHT_DOWNLOAD_HOST` 国内镜像 |

---

## 8. 能力等级（L1-L4）

| 等级 | 表现 |
|---|---|
| L1 | 能安装 Playwright、跑通 `demo_app`、写出 1 个 PageObject、跑通 `test_buy_flow.py` |
| L2 | 能完成 PageObject 分层、加上 CI、失败截图/录视频、Allure 报告可看、造数脚本跑通 |
| L3 | 能把 PageObject 重构为 Screenplay、设计多项目共享的脚手架模板、接入数据池 Provider、实现 UI 造数与性能测试的流水线衔接 |
| L4 | 能沉淀企业级 UI 自动化平台：设备池管理、用例市场、报告聚合看板、自动化分析根因、与研发约定 `resourceId` 不变的治理流程 |

---

## 9. 附：最小可运行示例（HTTP）

以 `demo_app` 登录→建单为例，替换 `BASE_URL` 即可复用：

```bash
# 1) 启动被测前端
python -m uvicorn demo_app.main:app --port 8080 &

# 2) 跑通功能验证 + 造数
python -m pytest tests/ -v
# 9 passed (test_demo_api 6 + test_buy_flow 2 + test_seed_data 1)

# 3) 一键全链路：功能验证 → 造数 10 单 → 触发性能
bash scripts/run_web_tests.sh && python scripts/seed_data.py --web --count 10 && python scripts/trigger_perf.py
```

---

## 10. 实测验证记录（真实环境）

> 以下为 `project/web` 工程在真实环境下的实测证据（2026-08 实测），可直接复现核对。

**本地 demo 后端（无头浏览器全绿）**

```bash
python -m uvicorn demo_app.main:app --port 8080 &   # 启动被测前端
python -m pytest tests/ -v                          # 运行全部 Web 用例
```

| 用例文件 | 内容 | 实测结果 |
|---|---|---|
| `tests/test_demo_api.py` | 6 个接口用例（health / 页面 / 登录 / 未授权 401），无需浏览器 | 6 passed |
| `tests/test_buy_flow.py` | 登录报错提示、登录→加购→结算→建单（无头 Chrome 驱动） | 2 passed |
| `tests/test_seed_data.py` | UI 造数循环走单并落盘 CSV | 1 passed |

**真实站点验证（百度）**

```bash
python scripts/baidu_smoke.py "什么是智能测试" /tmp/baidu_result.png
```

打开 `https://www.baidu.com/` → 输入框输入"什么是智能测试" → 提交 → 结果页返回 **20 条真实结果**，页面标题"什么是智能测试_百度搜索"，截图保存于 `/tmp/baidu_result.png`。前置条件：本机安装 Chrome 且 `conftest.py` 以 `channel="chrome"` 启动；百度对无头访问有反爬校验，脚本内置 `--disable-blink-features=AutomationControlled` 并覆写 `navigator.webdriver` 规避。

---

*参考：第 2 章 §2.1 Web 自动化、project/web/ 工程、被测应用设计手稿.md（8 步业务链路）、Skill-16 多协议性能脚本构建（同模板）*