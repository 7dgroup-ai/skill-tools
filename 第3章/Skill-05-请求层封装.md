# Skill-05-请求层封装

> **能力名称**：请求层封装（多协议 Client + 认证链 + 统一断言）
> **生命周期阶段**：准备/构建
> **资产来源**：第 3 章 §3.1 请求层封装；project/clients/、project/asserters/、project/tests/test_http_client.py、test_auth.py、test_schema_validator.py
> **文档版本**：v1.0 | 维护者：李文 | 更新日期：2026-08-06

---

## 0. 一句话定位

把"用 requests 发一个请求"升级为"多协议 + 认证 + 断言"三合一的统一请求层——定义 `IClient` 统一契约，把多协议（REST/gRPC/GraphQL/WS）、认证链、断言收口到 `clients/`、`asserters/` 两层，业务用例只关心"调哪个接口、传什么参数、期望什么结果"。

---

## 1. 触发场景（何时调用）

- [ ] 业务链路横跨 REST / gRPC / GraphQL / WebSocket 多协议，需统一调用方式避免用例层感知协议差异
- [ ] 认证逻辑散落在各用例（手动取 token、塞 header、处理 401），需集中到 Client 层实现"取令牌 → 注入请求 → 401 自动刷新重试"
- [ ] 断言散落在用例（裸 `assert resp.status_code == 200`），需封装为 Schema 校验 + 业务断言链，做到可复用、可判定
- [ ] 需要让编排层（DSL，Skill-07）以统一契约 `ApiRequest/ApiResponse` 调度多协议，不感知协议细节

> 不需要此 Skill 的场景：仅单协议 HTTP、无认证、仅做简单功能验证（直接用 httpx/pytest 即可）、无编排层/DSL 需求。

---

## 2. 输入契约（Input Contract）

| 项 | 必备/可选 | 说明 |
|---|---|---|
| 被测系统基础 URL | 必备 | 如 `http://localhost:8000`，需可直接访问 |
| 协议类型与版本 | 必备 | REST（HTTP/1.1/2）、gRPC（需 .proto）、GraphQL（需 schema）、WS（需握手端点） |
| 认证方式与凭据 | 必备 | JWT（登录接口/刷新端点）、OAuth2（client_id/secret）、AK-SK（AccessKey/SecretKey） |
| `.proto` / GraphQL Schema | 可选 | gRPC/GraphQL 场景必备，需编译生成存根/类型定义 |
| Python 环境 | 必备 | Python 3.10+，可安装 httpx/grpcio/websockets/pytest |

**入口检查清单**：
- [ ] `pip install -r requirements.txt` 成功，`import httpx/grpcio/websockets` 无报错
- [ ] 至少 1 个真实可访问的端点（REST `/health` 返回 `{"code":0,"msg":"ok"}`）
- [ ] 认证策略已明确：JWT（登录接口/刷新端点/过期时间）、或 OAuth2/AK-SK 端点与凭据
- [ ] 明确"响应成功"的断言口径：HTTP 200 + 业务码 `code=0` + 关键字段非空

---

## 3. 工具链（Toolchain）

| 工具 | 版本 | 角色 | 备选 |
|---|---|---|---|
| httpx | ≥0.27 | REST/GraphQL 核心驱动 | requests / aiohttp |
| grpcio + protobuf | ≥1.60 | gRPC 客户端 | — |
| websockets | ≥12 | WebSocket 长连接 | — |
| pydantic | ≥2.5 | 请求/响应对象建模、校验 | dataclasses + typing |
| jsonschema | ≥4.20 | Schema 校验 | — |
| pytest | ≥8.0 | 测试运行器 | — |
| pytest-asyncio | ≥0.23 | 异步测试支持 | — |

**选型决策树**：
1. 仅 REST/GraphQL → `httpx` + `pydantic` + `jsonschema`
2. 需 gRPC → 加 `grpcio` + `protobuf`，需 `.proto` 编译产物
3. 需 WebSocket 长连接 → 加 `websockets`
4. 仅同步调用 → 无需 `pytest-asyncio`；异步场景需加

> 炼手建议：先跑通 `tests/test_http_client.py`（REST + JWT），再逐个加入 gRPC/WS 客户端实现，每加一个跑一次 `pytest -k grpc` / `pytest -k ws` 确认通过。

---

## 4. 执行步骤

### 4.1 统一契约（`clients/base.py`）

```python
# project/clients/base.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Optional

@dataclass
class ApiRequest:
    path: str
    method: str = "GET"
    headers: dict[str, str] = field(default_factory=dict)
    params: dict[str, Any] = field(default_factory=dict)
    body: Any = None
    timeout: float = 10.0

@dataclass
class ApiResponse:
    status_code: int
    body: Any
    raw: bytes = b""
    elapsed_ms: float = 0.0
    headers: dict[str, str] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 300

class IClient:
    def request(self, req: ApiRequest, **ctx: Any) -> ApiResponse:
        raise NotImplementedError
    def close(self) -> None:
        raise NotImplementedError
```

### 4.2 REST 客户端（`clients/http_client.py`）

```python
# project/clients/http_client.py
import httpx
from .base import IClient, ApiRequest, ApiResponse

class HttpClient(IClient):
    def __init__(self, base_url: str, timeout: float = 10.0):
        self._client = httpx.AsyncClient(base_url=base_url, timeout=timeout)

    async def request(self, req: ApiRequest, **ctx) -> ApiResponse:
        import time
        start = time.perf_counter()
        r = await self._client.request(
            req.method, req.path, params=req.params, headers=req.headers,
            json=req.body if isinstance(req.body, dict) else None, content=req.body)
        elapsed = (time.perf_counter() - start) * 1000
        return ApiResponse(status_code=r.status_code, body=r.json() if r.is_json else r.text,
                           raw=r.content, elapsed_ms=elapsed, headers=dict(r.headers))

    async def close(self):
        await self._client.aclose()
```

### 4.3 认证链（`clients/auth.py`）——核心：挂在 Client 层，自动取令牌→注入→401 刷新重试

```python
# project/clients/auth.py
import threading
from .base import ApiRequest

class AuthStrategy:
    def acquire(self) -> str: raise NotImplementedError
    def refresh(self, token: str) -> str: raise NotImplementedError

class JWTStrategy(AuthStrategy):
    def __init__(self, client, login_path: str, username: str, password: str):
        self._client = client; self._login_path = login_path
        self._username, self._password = username, password

    def acquire(self) -> str:
        r = self._client.request(ApiRequest(self._login_path, "POST",
                         body={"username": self._username, "password": self._password}))
        return r.body["data"]["token"]

    def refresh(self, token: str) -> str:
        # 假设有刷新端点 /api/auth/refresh
        r = self._client.request(ApiRequest("/api/auth/refresh", "POST",
                         headers={"Authorization": f"Bearer {token}"}))
        return r.body["data"]["token"]

class AuthManager:
    def __init__(self, strategy):
        self._strategy = strategy
        self._token = None
        self._lock = threading.Lock()

    def ensure(self, req: ApiRequest) -> ApiRequest:
        with self._lock:
            if self._token is None:
                self._token = self._strategy.acquire()
        req.headers["Authorization"] = f"Bearer {self._token}"
        return req

    def on_401(self) -> bool:
        """401 时尝试刷新一次，成功返回 True。"""
        with self._lock:
            try:
                self._token = self._strategy.refresh(self._token)
                return True
            except Exception:
                self._token = None
                return False
```

### 4.4 统一断言（`asserters/`）

```python
# project/asserters/schema_validator.py
import jsonschema
from .business_assert import BusinessAssert

USER_LOGIN_SCHEMA = {
    "type": "object", "required": ["code", "data"],
    "properties": {
        "code": {"type": "integer"},
        "data": {"type": "object", "required": ["token"], "properties": {"token": {"type": "string"}}}
    }
}

def assert_schema(body: dict, schema: dict):
    jsonschema.validate(instance=body, schema=schema)

# project/asserters/business_assert.py
class BusinessAssert:
    def __init__(self, body: dict):
        self._body = body
        self._ok = True
        self._errors = []

    def http_ok(self) -> "BusinessAssert":
        if not self._body.get("code") == 0:
            self._ok = False
            self._errors.append(f"业务码非 0: {self._body}")
        return self

    def biz_code(self, code: int) -> "BusinessAssert":
        if self._body.get("code") != code:
            self._ok = False
            self._errors.append(f"期望业务码 {code}, 实际 {self._body.get('code')}")
        return self

    def field(self, jsonpath: str, predicate=None) -> "BusinessAssert":
        # 简化：直接取 body 字段
        val = self._body
        for k in jsonpath.strip("$.").split("."):
            val = val.get(k)
            if val is None: break
        if predicate and not predicate(val):
            self._ok = False
            self._errors.append(f"字段 {jsonpath} 值 {val} 不满足谓词")
        elif val is None:
            self._ok = False
            self._errors.append(f"字段 {jsonpath} 不存在")
        return self

    def assert_pass(self):
        assert self._ok, "; ".join(self._errors)
```

---

## 5. 输出契约（Output Contract）

| 产物 | 说明 |
|---|---|
| `project/clients/` | 统一契约 `IClient` + 4 个协议实现 + `AuthManager` |
| `project/asserters/` | `schema_validator.py` + `business_assert.py` |
| 运行证明 | `pytest tests/test_http_client.py tests/test_auth.py tests/test_schema_validator.py -v` 全绿 |
| 接口说明 | 各协议 Client 入参/出参、认证策略接口、断言链用法 |

**验收前必须能当面演示**：
```bash
cd project
pip install -r requirements.txt
pytest tests/test_http_client.py tests/test_auth.py tests/test_schema_validator.py -v
# test_http_client.py::test_get_goods_list_ok PASSED
# test_http_client.py::test_login_and_http_ok PASSED
# test_auth.py::test_jwt_strategy_acquires_token PASSED
# test_schema_validator.py::test_valid_login_body_passes_schema PASSED
# test_schema_validator.py::test_business_assert_chain PASSED
# ... 共 17 个测试全部通过
```

---

## 6. 验收清单（Acceptance Checklist）

- [ ] `IClient` 统一契约已定义，`HttpClient`/`GrpcClient`/`GraphQLClient`/`WsClient` 四类实现齐备
- [ ] `AuthManager` 实现：JWT 策略（登录取 token / 401 刷新重试 / 线程安全互斥锁）
- [ ] `BusinessAssert` 链式断言：`http_ok().biz_code(0).field("$.data.token", len>=20)` 可一行串完
- [ ] Schema 校验：`assert_schema(body, USER_LOGIN_SCHEMA)` 可结构化校验响应结构
- [ ] 单元测试全绿：`pytest tests/test_http_client.py tests/test_auth.py tests/test_schema_validator.py -v`（17 项通过）
- [ ] 无敏感信息写入代码（token/密码/内网地址均用 `${var}` 占位）
- [ ] 所有 `localhost:8000` 类地址标注"替换为你的被测系统"

---

## 7. 常见坑点（Pitfalls）

| 现象 | 原因 | 排查 |
|---|---|---|
| gRPC 连接失败 | `.proto` 未编译 / 端口错误 / TLS 证书 | `python -m grpc_tools.protoc` 重新编译；检查端口/TLS 配置 |
| WebSocket 连接断开 | 心跳未发 / 服务端主动断开 | 实现心跳 `ping/pong`；捕获 `ConnectionClosed` 自动重连 |
| Token 并发竞态 | 多线程同时取/刷 token | `AuthManager._lock` 互斥锁保护 `acquire/refresh` |
| 断言链中断 | 某步 `return self` 忘写 / 谓词报错 | 链式方法必须 `return self`；谓词用 `try/except` 兜底 |
| Schema 校验过严 | 响应多余字段导致校验失败 | Schema 用 `additionalProperties: true` 或仅校验必填字段 |

---

## 8. 能力等级（L1-L4）

| 等级 | 表现 |
|---|---|
| L1 | 能跑通 `HttpClient` + JWT 登录 + 业务断言链，跑通单元测试 |
| L2 | 能补全 `GrpcClient`/`WsClient`、补全 `AuthStrategy` 子类（OAuth2/AK-SK）、补全 Schema 校验 |
| L3 | 能设计多协议统一网关、认证策略插件化、断言链插件化、封装企业级 `ApiClient` SDK 给多项目复用 |
| L4 | 能沉淀企业级请求层平台：协议自动识别、认证策略热插拔、断言规则可视化配置、全链路追踪集成 |

---

## 9. 附：最小可运行示例（REST + JWT）

```bash
cd project
pip install -r requirements.txt
pytest tests/test_http_client.py tests/test_auth.py -v
# test_http_client.py::test_login_and_http_ok PASSED
# test_auth.py::test_jwt_strategy_acquires_token PASSED
```

---

*参考：第 3 章 §3.1 请求层封装、project/clients/、project/asserters/、project/tests/、Skill-16 多协议性能脚本构建（同模板）*