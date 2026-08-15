# Skill-08-Mock 服务与契约测试

> **能力名称**：Mock 服务与契约测试（Python 内嵌 Mock / WireMock 独立部署 + Pact 消费者驱动契约 + OpenAPI Diff 破坏性判定）
> **生命周期阶段**：构建/执行
> **资产来源**：第 3 章 §3.4.3 Mock 服务、§3.5 契约测试与 API 变更检测；project/mocks/、project/contract/、project/tests/test_mock_server.py、test_openapi_diff.py
> **文档版本**：v1.0 | 维护者：李文 | 更新日期：2026-08-06

---

## 0. 一句话定位

把"依赖不可控、变更崩溃"变成"下游可隔离、异常可注入、变更可感知"——**Mock** 解决下游隔离与异常注入，**契约测试** 解决接口变更感知，**OpenAPI Diff** 兜底变更检测，三层防线把依赖风险收口在接口层。

---

## 1. 触发场景（何时调用）

- [ ] 被测系统依赖外部服务（支付/短信/第三方 API），环境不可控、需隔离下游、需注入失败/延迟验证降级逻辑
- [ ] 接口变更频繁，上游改字段导致下游崩溃，需**消费者驱动契约**（Pact）：下游定契约、上游发布前回放验证
- [ ] 不引入 Pact 时，需对新旧 OpenAPI 逐字段对比，按"破坏性/兼容性"四维度判定（必填被删/可选变必填/类型收紧/枚举缩小）
- [ ] 需**双跑策略**：契约绿后仍跑一条真实集成冒烟，两者结合才算完整

> 不需要此 Skill 的场景：无外部依赖、接口极其稳定不变更、仅内部服务且可直接联调、预算/人力不足以维护契约基础设施。

---

## 2. 输入契约（Input Contract）

| 项 | 必备/可选 | 说明 |
|---|---|---|
| 被测系统依赖的外部服务契约 | 必备 | OpenAPI Spec / gRPC proto / Pact 文件，需明确请求/响应结构 |
| 被测系统代码库访问权限 | 必备 | 生产者侧回放需启动真实服务 |
| Pact Broker 部署 | 可选 | Pact 协作需 Broker 存储/版本化/通知；单机可用文件级 Pact |
| WireMock 独立部署 | 可选 | 多团队共享、契约稳定的外部依赖（支付/短信） |
| Python 环境 | 必备 | Python 3.10+，可安装 pact-python/wiremock/fastapi |

**入口检查清单**：
- [ ] `pip install pact-python wiremock` 无报错
- [ ] `pact-broker` 启动可访问（或文件级 Pact 文件可读写）
- [ ] `python -m pytest tests/test_mock_server.py -v` 全绿（Mock 服务可用）
- [ ] `python -m pytest tests/test_openapi_diff.py -v` 全绿（破坏性判定正确）

---

## 3. 工具链（Toolchain）

| 工具 | 版本 | 角色 | 备选 |
|---|---|---|---|
| pact-python | ≥2.2 | 消费者录制 / 生产者回放 | — |
| pact-broker | 2.x | 契约存储/版本化/通知 | 文件级 Pact（单机） |
| wiremock | ≥3.0 | 独立 Mock 服务 | Python 内嵌 Mock（`mocks/app.py`） |
| fastapi | ≥0.110 | 内嵌 Mock 服务 | Flask / Starlette |
| openapi-spec-validator | ≥0.5 | OpenAPI Spec 校验 | — |
| pytest | ≥8.0 | 测试运行器 | — |

---

## 4. 执行步骤

### 4.1 Python 内嵌 Mock（`project/mocks/app.py`）——快速闭环首选

```python
# project/mocks/app.py
from fastapi import FastAPI, Response
import time

app = FastAPI()

@app.post("/pay")
def pay(resp: Response, fail_rate: float = 0.0, delay_ms: int = 0):
    """支付 Mock：fail_rate 注入失败、delay_ms 注入超时。"""
    if delay_ms:
        time.sleep(delay_ms / 1000)
    if fail_rate and (hash(str(time.time_ns())) % 100) / 100 < fail_rate:
        resp.status_code = 503
        return {"code": -1, "msg": "payment provider unavailable"}
    return {"code": 0, "transaction_id": f"tx-{time.time_ns()}"}
```

**两大核心参数**：
- `fail_rate: float` —— 失败概率（0.0~1.0），用于验证降级与重试逻辑
- `delay_ms: int` —— 注入延迟毫秒数，用于验证超时兜底与重试上限

> **异常注入的关键是"可配置的随机性"**：`fail_rate` 让失败以概率出现，验证降级与重试；`delay_ms` 制造超时，验证超时兜底与重试上限。

### 4.2 WireMock 独立部署（多团队共享、契约稳定）

```bash
# 1) 启动 WireMock 容器
docker run -d -p 8080:8080 -v $(pwd)/wiremock:/home/wiremock wiremock/wiremock:3.0

# 2) 编写桩文件（wiremock/mappings/pay.json）
{
  "request": { "method": "POST", "urlPath": "/pay" },
  "response": { "status": 200, "jsonBody": { "code": 0, "transaction_id": "tx-mock" } }
}

# 3) 编写故障桩（wiremock/__files/pay_503.json）
{
  "request": { "method": "POST", "urlPath": "/pay", "queryParameters": { "fail": { "equalTo": "1" } } },
  "response": { "status": 503, "jsonBody": { "code": -1, "msg": "unavailable" } }
}
```

> **何时用哪种**：独立 WireMock 适合"契约已稳定、多团队共享"的外部依赖（支付/短信），一套桩可在多个被测系统间复用；Python 内嵌 Mock 适合"本工程快速闭环、需现场改失败率/延迟"的场景——参数直接暴露在函数签名里，用例无需重启服务即可注入异常。

### 4.3 Pact 消费者驱动契约（Consumer → Broker → Provider）

```python
# project/contract/pact_consumer.py
from pact import Consumer, Provider

def build_pact():
    pact = Consumer("order-service").has_pact_with(Provider("payment-service"))
    pact.given("订单存在").upon_receiving("支付订单") \
        .with_request("POST", "/pay",
            body={"order_id": "order-123", "amount": 19.9}) \
        .will_respond_with(200, body={"code": 0, "transaction_id": "tx-1"})
    return pact

# 消费者侧：运行用例录制契约
def test_pact_consumer():
    pact = build_pact()
    with pact:
        # 真实调用 Mock Server（pact 启动内置 Mock）
        resp = requests.post(pact.uri + "/pay", json={"order_id": "order-123", "amount": 19.9})
        assert resp.json()["code"] == 0
    # pact 自动写入 pact/order-service-payment-service.json
```

**生产者侧回放（契约的另一半）**：
```bash
pact-provider-verifier \
  --provider-base-url http://localhost:8000 \
  --pact-broker-base-url http://pact-broker:9292 \
  --provider payment-service
```

| 角色 | 动作 | 产出 |
|---|---|---|
| **消费者** | 运行用例录制契约 | Pact 文件（JSON） |
| **Broker** | 存储契约、版本化、通知 | pact-broker 服务 |
| **生产者** | 发布前回放契约验证 | 验证通过才可上线 |

### 4.4 OpenAPI Diff（不引入 Pact 时的兜底）

```python
# project/contract/openapi_diff.py
def diff_compat(old: dict, new: dict) -> list[Change]:
    changes = []
    # ① 接口/路径被删
    for p in set(old["paths"]) - set(new["paths"]):
        changes.append(Change(p, "remove_path", breaking=True))
    # 遍历公共路径
    for p in set(old["paths"]) & set(new["paths"]):
        old_op, new_op = old["paths"][p].get("post", {}), new["paths"][p].get("post", {})
        if not old_op or not new_op: continue
        old_req, new_req = set(old_op.get("required", [])), set(new_op.get("required", []))
        # ① 必填被删
        for field in old_req - new_req:
            changes.append(Change(f"{p}.{field}", "required_removed", breaking=True))
        # ② 可选变必填
        for field in new_req - old_req:
            changes.append(Change(f"{p}.{field}", "required_added", breaking=True))
        # ③ 类型收紧 / ④ 枚举缩小
        for name, os_, ns_ in _field_schemas(old_op, new_op):
            if _type_tightened(os_, ns_):
                changes.append(Change(f"{p}.{name}", "type_tightened", breaking=True))
            if set(os_.get("enum", [])) - set(ns_.get("enum", [])):
                changes.append(Change(f"{p}.{name}", "enum_shrunk", breaking=True))
    return changes
```

**四维破坏性判定**：
| 变更类型 | 破坏性 | 示例 |
|---|:---:|---|
| 删除接口/字段 | 破坏 | 删 `order_id` 必填字段 |
| 可选字段被新增为必填 | 破坏 | `token` 由可选→必填 |
| 字段类型收紧 | 破坏 | `amount` 由 number→integer |
| 缩小枚举取值 | 破坏 | `status` 由 [PENDING,PAID,CANCEL]→[PAID] |
| 新增可选字段 | 兼容 | 新增 `remark` 可选 |
| 新增接口 | 兼容 | 新增 `GET /api/coupon` |

> **分级不是学术分类，而是门禁动作的输入**——破坏性变更必须走评审并通知所有下游，兼容性变更可自动放行。

### 4.5 双跑策略（⚠️ 关键）

> **契约测试通过 ≠ 真实集成通过**——它验证的是"约定"而不是"联调"。契约绿后仍要跑一条**真实集成冒烟**（两端真实服务联调），两者结合才算完整：
> - 契约测试解决"变更感知"成本
> - 真实集成解决"真实链路"质量

```bash
# 1) 消费者录制契约
pytest tests/test_pact_consumer.py -v

# 2) 生产者回放验证（CI 门禁）
pact-provider-verifier --provider-base-url http://localhost:8000 \
  --pact-broker-base-url http://pact-broker:9292 --provider payment-service

# 3) 真实集成冒烟（契约绿后仍需跑）
pytest tests/test_integration_smoke.py -v
```

---

## 5. 输出契约（Output Contract）

| 产物 | 说明 |
|---|---|
| `project/mocks/app.py` | Python 内嵌 Mock（支付/短信，支持 fail_rate/delay_ms） |
| `project/contract/pact_consumer.py` | 消费者契约录制代码 |
| `project/contract/openapi_diff.py` | OpenAPI Diff 四维破坏性判定 |
| `project/tests/test_mock_server.py` | Mock 服务验收用例 |
| `project/tests/test_openapi_diff.py` | Diff 破坏性判定验收用例 |
| Pact 文件 | `pact/order-service-payment-service.json`（上传 Broker） |

**验收前必须能当面演示**：
```bash
# 1) Mock 服务验收
pytest tests/test_mock_server.py -v
# test_pay_ok PASSED
# test_pay_always_fail PASSED
# test_pay_delay_injectable PASSED

# 2) OpenAPI Diff 破坏性判定
pytest tests/test_openapi_diff.py -v
# test_breaking_change_required_field_removed PASSED
# test_breaking_change_path_removed PASSED
# test_compatible_change_add_path PASSED

# 3) Pact 消费者录制（需 pact-broker 运行）
pytest tests/test_pact_consumer.py -v

# 4) 生产者回放（需 pact-broker + 生产者服务运行）
pact-provider-verifier --provider-base-url http://localhost:8000 \
  --pact-broker-base-url http://pact-broker:9292 --provider payment-service
```

---

## 6. 验收清单（Acceptance Checklist）

- [ ] `pytest tests/test_mock_server.py -v` 全绿（支付 Mock 可注入 fail_rate/delay_ms）
- [ ] `pytest tests/test_openapi_diff.py -v` 全绿（四维破坏性判定正确：删必填/可选变必填/类型收紧/枚举缩小 → 破坏；加可选字段/加接口 → 兼容）
- [ ] 消费者侧 `pytest test_pact_consumer.py` 录制 Pact 文件并上传 Broker
- [ ] 生产者侧 `pact-provider-verifier` 回放通过；生产者"改了响应字段"后回放**失败**；回退后恢复绿色
- [ ] 契约绿后仍保留一条真实集成冒烟用例（双跑策略）
- [ ] 无敏感信息写入 Pact 文件/Mock 代码（Token/密码/内网地址用占位符）

---

## 7. 常见坑点（Pitfalls）

| 现象 | 原因 | 排查 |
|---|---|---|
| Mock 失败不触发 | `fail_rate` 算法导致概率不稳定 / 参数未传 | `hash(time.time_ns()) % 100` 确保均匀；确认参数透传到 Mock 函数 |
| Pact 回放失败 | 请求/响应字段不匹配 / Broker 版本不一致 | 对比 Pact 文件与实际请求；Broker 版本兼容性 |
| Diff 误报 | Spec 里 `$ref` 未解析 / `required` 写法不标准 | 先 `openapi-spec-validator` 校验 Spec；展开 `$ref` 再 Diff |
| 契约绿但线上崩 | 双跑策略未落实 / 冒烟用例缺失 | 必须保留真实集成冒烟；契约只验"约定"不验"联调" |
| Mock 参数不生效 | FastAPI 依赖注入参数写法错误 | `fail_rate: float = 0.0` 必须有默认值；`resp: Response` 用于设置状态码 |

---

## 8. 能力等级（L1-L4）

| 等级 | 表现 |
|---|---|
| L1 | 能跑通内嵌 Mock（fail_rate/delay_ms）、跑通 OpenAPI Diff 四维判定、理解 Pact 消费者/生产者角色 |
| L2 | 能部署 WireMock、编写 Pact 消费者录制、配置 pact-broker、配置生产者回放 CI、编写 OpenAPI Diff 规则 |
| L3 | 能设计 Mock 服务治理（版本化/多环境/多团队共享）、设计契约演进策略（版本化/兼容性矩阵/自动化门禁） |
| L4 | 能搭建企业级契约治理平台：Mock 市场、契约市场、自动化变更影响分析、跨团队契约协作、与 CI/CD/监控全打通 |

---

## 9. 附：最小可运行示例

```bash
cd project

# 1) Mock 服务验收
pytest tests/test_mock_server.py -v
# test_pay_ok PASSED
# test_pay_always_fail PASSED
# test_pay_delay_injectable PASSED

# 2) OpenAPI Diff 验收
pytest tests/test_openapi_diff.py -v
# test_breaking_change_required_field_removed PASSED
# test_breaking_change_path_removed PASSED
# test_compatible_change_add_path PASSED
```

---

*参考：第 3 章 §3.4.3 Mock 服务、§3.5 契约测试与 API 变更检测、project/mocks/、project/contract/、project/tests/test_mock_server.py、test_openapi_diff.py、Skill-16 多协议性能脚本构建（同模板）*