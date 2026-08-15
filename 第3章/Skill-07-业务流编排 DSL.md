# Skill-07-业务流编排 DSL

> **能力名称**：业务流编排 DSL（YAML 场景 + 关联/重试/前后置/清洗/分支循环 + OpenAPI 驱动 + Mock/契约复用）
> **生命周期阶段**：构建/执行
> **资产来源**：第 3 章 §3.4 业务流编排 DSL；project/dsl/、project/scenarios/、project/tests/test_dsl_runner.py
> **文档版本**：v1.0 | 维护者：李文 | 更新日期：2026-08-06

---

## 0. 一句话定位

把"散落的用例脚本"升级为"YAML 声明的业务流"——步骤、关联、数据清洗、失败重试、前后置、分支循环全声明化；OpenAPI 自动生成骨架；Mock/契约复用；用例只写"业务意图"，不写实现细节。

---

## 1. 触发场景（何时调用）

- [ ] 多条接口需编排成业务流（登录 → 加购 → 预览 → 建单 → 支付 → 查单），步骤间有数据关联（token、orderId）
- [ ] 步骤需声明式配置：关联（extract）、重试（retry，含异常级+指数退避）、前后置、数据清洗、条件分支、循环
- [ ] 失败需可观测：每步结构化日志含 `request_id`、`attempt`、`elapsed_ms`，重试真实发生可断言
- [ ] OpenAPI/Swagger 已有，需自动生成用例骨架（路径/方法/参数），人工补业务断言
- [ ] 同一份 YAML 需同时被接口测试（校验模式）与性能测试（发压模式）复用，避免双份维护
- [ ] 需与 Mock（Skill-08）、契约（Skill-08）、数据工厂（Skill-06）、请求层（Skill-05）无缝集成

> 不需要此 Skill 的场景：单接口验证、无数据关联、无重试/分支/循环需求、仅做简单接口测试（直接用 pytest + httpx 即可）。

---

## 2. 输入契约（Input Contract）

| 项 | 必备/可选 | 说明 |
|---|---|---|
| YAML 场景文件 | 必备 | 符合 DSL 结构的 `.yaml`（见 §4.1 结构定义） |
| 请求层 Client | 必备 | 实现 `IClient` 的实例（Skill-05 产出） |
| 数据工厂 | 必备 | `DataFactory` 实例（Skill-06 产出） |
| 认证管理器 | 必备 | `AuthManager` 实例（Skill-05 产出） |
| OpenAPI Spec（可选） | 可选 | 用于自动生成场景骨架（`dsl/openapi_gen.py`） |
| Mock 服务（可选） | 可选 | 内嵌 Mock 或 WireMock 地址（Skill-08 产出） |

**入口检查清单**：
- [ ] `pip install -r requirements.txt` 成功，`import yaml/jsonpath_ng` 无报错
- [ ] `ScenarioRunner(client, factory, auth).run(scenario)` 能跑通 `scenarios/order_flow.yaml`
- [ ] 步骤间 `${token}`、`${order_id}` 关联自动生效，无手工拼接
- [ ] 支付步骤注入 503 时触发重试并最终成功；注入超时（`delay_ms=2000`）触发异常级重试而非崩溃
- [ ] 分支（`if`）与循环（`foreach`）按预期执行
- [ ] `clean` 数据清洗（round/trim/default）在步骤间生效

---

## 3. 工具链（Toolchain）

| 工具 | 版本 | 角色 | 备选 |
|---|---|---|---|
| PyYAML | ≥6.0 | YAML 解析/生成 | — |
| jsonpath-ng | ≥1.5 | JSONPath 提取 | jmespath |
| jsonschema | ≥4.20 | OpenAPI Spec 校验 | — |
| OpenAPI Spec | — | 源 Spec（生成骨架用） | — |
| pytest | ≥8.0 | 测试运行器 | — |
| httpx | ≥0.27 | 执行引擎底层驱动 | — |

---

## 4. 执行步骤

### 4.1 YAML 场景结构（完整声明式）

```yaml
# project/scenarios/order_flow.yaml
name: order_flow
description: "登录 → 加购 → 预览 → 建单 → 支付 → 查单"
base_url: http://localhost:8000
auth: {type: jwt, username: ${user}, password: ${password}}   # Provider 注入

setup:
  - data: normal_order        # 调用数据工厂准备订单
  - mock: payment             # 打开支付 Mock（隔离外部支付）

steps:
  - name: login
    request: {path: /api/login, method: POST, body: {username: ${user}, password: ${password}}}
    extract: {token: {path: "$.data.token", method: jsonpath}}   # 关联：供后续步骤使用
    assert: {biz_code: 0}

  - name: add_to_cart
    request: {path: /api/cart/add, method: POST, body: {goods_id: ${goods_id}, num: 1}}
    auth: ${token}                                               # 自动注入已提取 token
    retry: {times: 2, on: [429, 503], backoff: {base: 0.5, jitter: 0.2}}  # 重试 + 指数退避
    assert: {biz_code: 0}

  - name: pay_order
    request: {path: /api/order/pay, method: POST, body: {order_id: ${order_id}, pay_type: mock}}
    assert:
      http_ok: true
      biz_code: 0

teardown:
  - cleanup: {type: soft_delete, keys: [order_id]}               # 软删除订单，避免脏数据
  - mock_off: payment
```

**核心字段说明**：
| 字段 | 含义 |
|---|---|
| `setup` | 前置：数据工厂造数、开 Mock、前置条件 |
| `steps` | 主链路：每步含 `request`/`extract`/`retry`/`assert`/`clean`/`if`/`foreach` |
| `teardown` | 后置：清理数据、关 Mock、释放资源，**失败用例也会执行** |
| `extract` | 关联：从响应提取值进上下文 `${var}`，支持 `jsonpath/regex/schema` |
| `retry` | 重试：`times` 次、`on` 状态码、`backoff.base/jitter` 指数退避，**异常级同步重试** |
| `clean` | 数据清洗：`{field: ${total}, op: round, args: [2]}` 归一化（round/trim/default） |
| `if` / `foreach` | 条件分支 / 循环，支持嵌套 `steps` |

### 4.2 执行引擎（`project/dsl/runner.py`）

```python
# project/dsl/runner.py
class ScenarioRunner:
    def __init__(self, client: IClient, factory: DataFactory, auth: AuthManager):
        self._client, self._factory, self._auth = client, factory, auth
        self._ctx: dict = {}

    def run(self, scenario: dict) -> list[StepResult]:
        results = []
        self._setup(scenario.get("setup", []))
        for step in scenario["steps"]:
            results.append(self._exec_step(step))
        self._teardown(scenario.get("teardown", []))
        return results

    def _exec_step(self, step: dict) -> StepResult:
        req_spec = step["request"]
        retry = step.get("retry", {})
        times = retry.get("times", 0)
        last_resp = None
        for attempt in range(1 + times):
            try:
                req = self._build_request(req_spec)      # 每次重试重建请求（token 可能已刷新）
                last_resp = self._client.request(req)
            except (TimeoutError, ConnectError) as e:   # 异常同样可重试（超时/连不上）
                if attempt < times:
                    self._sleep_backoff(attempt, retry)
                    continue
                break
            passed, reason = self._pass(step.get("assert", {}), last_resp)
            if passed:
                self._extract(step.get("extract", {}), last_resp)
                return StepResult(step["name"], True, last_resp, attempt + 1)
            if last_resp.status_code in retry.get("on", []):
                self._sleep_backoff(attempt, retry)
                continue
            break
        return StepResult(step["name"], False, last_resp, 1 + times, error=reason)

    def _sleep_backoff(self, attempt: int, retry: dict) -> None:
        import random, time
        b = retry.get("backoff", {}).get("base", 0.5)
        j = retry.get("backoff", {}).get("jitter", 0.2)
        time.sleep(b * (2 ** attempt) + random.uniform(0, j))
```

**重试语义**：覆盖**状态码级**（`on: [429, 503]`）与**异常级**（`TimeoutError`/`ConnectError`）。纯按状态码判断的重试无法覆盖超时：`request()` 抛异常时根本不进入断言，用例直接失败。**必须配指数退避**——8 步链路 × 100 并发时，同时重试会在同一秒压垮下游，`base * 2^n + jitter` 让重试在时间上错开。

### 4.3 分支与循环

```yaml
steps:
  - name: coupon_check
    request: {path: /api/coupon/query, method: GET, params: {user: ${user}}}
    extract: {has_coupon: {path: "$.data.has_coupon", method: jsonpath}}
    if: ${has_coupon} == "true"
    steps:
      - name: pay_with_coupon
        request: {path: /api/order/pay, method: POST,
                  body: {order_id: ${order_id}, pay_type: mock, coupon: "C001"}}

  - name: pay_each_cart_item
    foreach: ${cart_items}
    steps:
      - request: {path: /api/cart/pay, method: POST, body: {goods_id: ${item.id}}}
```

### 4.4 数据清洗（`clean`）

```yaml
steps:
  - name: calc_total
    request: {path: /api/order/preview, method: POST}
    extract: {total: {path: "$.data.total", method: jsonpath}}
    clean: {field: ${total}, op: round, args: [2]}   # 字符串→数字→保留 2 位小数
  - name: create_order
    request: {path: /api/order/create, method: POST, body: {amount: ${total}}}
```

---

## 5. 输出契约（Output Contract）

| 产物 | 说明 |
|---|---|
| `project/dsl/` | `runner.py` / `loader.py` / `openapi_gen.py` / `retry.py` |
| `project/scenarios/` | `order_flow.yaml` / `order_flow_variants.yaml` / `cart_add_variants.yaml` |
| 运行证明 | `pytest tests/test_dsl_runner.py -v` 全绿 |
| 执行日志 | 每步结构化日志：`request_id`、`attempt`、`elapsed_ms`、状态码/异常、输入输出 |

**验收前必须能当面演示**：
```bash
cd project
pytest tests/test_dsl_runner.py -v
# test_load_scenario_valid PASSED
# test_login_flow_runs PASSED
# test_order_flow_runs PASSED
# test_order_flow_fails_on_bad_user PASSED
```

---

## 6. 验收清单（Acceptance Checklist）

- [ ] `ScenarioRunner` 能加载并执行 `order_flow.yaml`，8 步全绿
- [ ] `${token}`、`${order_id}` 关联自动生效，无手工拼接
- [ ] `retry.on=[429,503]` 状态码级重试生效；异常级（Timeout/ConnectError）同样重试
- [ ] 指数退避 `base * 2^n + jitter` 生效，重试错开、不打挂下游
- [ ] `clean: {op: round, args: [2]}` 数据清洗生效
- [ ] `if: ${has_coupon} == "true"` 条件分支按预期走优惠/非优惠链路
- [ ] `foreach: ${cart_items}` 循环遍历购物车逐项结算
- [ ] `setup`/`teardown` 前后置执行，失败用例也执行 `teardown`（软删/关 Mock）
- [ ] 每步结构化日志含 `request_id`、`attempt`、`elapsed_ms`，`attempt>=2` 可断言重试真实发生
- [ ] `clean: {field: ${total}, op: round, args: [2]}` 金额归一化生效
- [ ] OpenAPI 生成骨架 `gen_scenarios_from_openapi(spec, base_url)` 产出合法 YAML 骨架

---

## 7. 常见坑点（Pitfalls）

| 现象 | 原因 | 排查 |
|---|---|---|
| 重试不触发 | `retry.on` 未包含实际状态码 / 异常未捕获 | 检查 `retry.on` 列表；捕获 `TimeoutError`/`ConnectError` |
| 重试风暴打挂下游 | 无退避 / 并发过大 | 必须配 `backoff.base` + `jitter`；并发限流 |
| 关联变量未生效 | `extract.path` 写错 / `method` 不匹配 | `jsonpath` 需 `[0]` 取首个；`regex` 需 `group(1)` |
| 变量泄露 | 上下文 `_ctx` 未隔离 | 每 `run()` 新建 `_ctx = {}`；并行跑需独立实例 |
| OpenAPI 生成骨架缺参数 | Spec 里 `parameters` 写法不标准 | 按 OpenAPI 3.0 规范写 `parameters`/`requestBody` |

---

## 8. 能力等级（L1-L4）

| 等级 | 表现 |
|---|---|
| L1 | 能跑通 `order_flow.yaml`，理解 YAML 结构、关联、重试、前后置 |
| L2 | 能写分支/循环/清洗、补全 `retry` 策略、补全 `clean` 操作、跑通变体场景 |
| L3 | 能设计 `ScenarioRunner` 扩展点（插件化 assert/extract/retry/clean）、OpenAPI 自动生成骨架、性能/验收双模式复用 |
| L4 | 能搭建企业级 DSL 平台：可视化编排器、版本化场景市场、并行执行引擎、全链路追踪、与 CI/CD/性能平台全打通 |

---

## 9. 附：最小可运行示例

```bash
cd project
python -m dsl.runner scenarios/order_flow.yaml
# Step login: PASSED (attempt=1, elapsed=45ms)
# Step add_to_cart: PASSED (attempt=1, elapsed=32ms)
# Step pay_order: PASSED (attempt=1, elapsed=28ms)
# All 3 steps passed.
```

---

## 10. 性能层复用边界（⚖️ 重要）

> **同一份 YAML 被第 5 章复用时切"发压模式"**：
> - `mode: verify`（接口测试）：逐条**校验返回值**，`assert` 全开
> - `mode: load`（性能脚本）：持续**发压且不阻塞校验**，跳过 `assert`、复用同一请求模板，加 `rate: <RPS>` 限流
> - **不要为两种用途维护两份场景**，否则接口改动要改两处。实现上开两个开关即可。

---

*参考：第 3 章 §3.4 业务流编排 DSL、project/dsl/、project/scenarios/、project/tests/test_dsl_runner.py、Skill-16 多协议性能脚本构建（同模板）*