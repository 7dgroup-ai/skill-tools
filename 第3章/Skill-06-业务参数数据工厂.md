# Skill-06-业务参数数据工厂

> **能力名称**：业务参数数据工厂（Builder/Factory/Provider 三层 + 提取器 + 隔离清理 + 血缘质量目录脱敏）
> **生命周期阶段**：构建
> **资产来源**：第 3 章 §3.3 业务参数数据工厂；project/datafactory/、project/tests/test_data_factory.py
> **文档版本**：v1.0 | 维护者：李文 | 更新日期：2026-08-06

---

## 0. 一句话定位

把"散落在用例里的造数逻辑"收口为三层——**Builder（怎么拼）→ Factory（怎么要）→ Provider（数据从哪来）**，叠加**提取器（JSONPath/正则/Schema）**、**隔离清理（池/事务/软删/TTL）**、**血缘质量目录脱敏**四大治理能力，让用例层只写"我要一个正常订单"，把造数复杂度全收口。

---

## 1. 触发场景（何时调用）

- [ ] 造数逻辑散落在各用例里（`user = {"username": "u_1", ...}` 满屏飞），维护成本高、难复用
- [ ] 并发用例取同一数据导致冲突、脏数据污染后续用例，需唯一性池/事务回滚/软删除/TTL 清理
- [ ] 造数依赖上游响应（token、orderId），需统一提取器（JSONPath/正则/Schema）供 DSL 关联
- [ ] 数据量大（性能测试需 10 万+ 参数），UI 造数不够，需接口批量造数 + Provider 池化
- [ ] 需数据治理：血缘追溯、质量门禁（完整性/唯一性/及时性/准确性）、元数据目录、敏感脱敏

> 不需要此 Skill 的场景：用例极少、造数极简（直接写死字典即可）、无并发、无治理要求。

---

## 2. 输入契约（Input Contract）

| 项 | 必备/可选 | 说明 |
|---|---|---|
| 数据源配置 | 必备 | CSV 目录（`DataProvider.from_csv("data")`）、或数据库连接串、或上游接口地址 |
| 业务实体定义 | 必备 | Builder 需要知道"正常订单/异常订单"各字段结构、必填/可选、边界值 |
| 唯一性键定义 | 必备 | Provider 池按什么键去重（如 `user_id`、`order_id`） |
| TTL/清理策略 | 可选 | 默认 1h TTL；长时/批量造数需显式配置 |
| 脱敏规则表 | 可选 | 默认手机/身份证/邮箱；特殊字段需补充 |

**入口检查清单**：
- [ ] `DataProvider.from_csv("data")` 能正确加载第 2 章产出的 CSV 文件
- [ ] `factory.normal_order()` 返回合法订单结构，字段完整、类型正确
- [ ] `provider.pool("users").take_unique()` 并发取 50 个用户无重复
- [ ] 池耗尽时抛 `DataPoolExhausted` 而非返回脏数据
- [ ] `TTLCleaner.sweep()` 能清扫过期记录并返回移除计数

---

## 3. 工具链（Toolchain）

| 工具 | 版本 | 角色 | 备选 |
|---|---|---|---|
| pydantic | ≥2.5 | Builder/实体建模、校验 | dataclasses + typing |
| jsonpath-ng | ≥1.5 | JSONPath 提取器 | jmespath |
| jsonschema | ≥4.20 | Schema 提取/校验 | — |
| re / json | 标准库 | 正则提取 / JSON 序列化 | — |
| threading | 标准库 | Provider 池并发互斥 | asyncio.Lock |
| time / uuid | 标准库 | TTL 时间戳 / 唯一键生成 | — |
| pytest | ≥8.0 | 测试运行器 | — |

---

## 4. 执行步骤

### 4.1 三层结构（Builder / Factory / Provider）

```python
# project/datafactory/builder.py
from pydantic import BaseModel, Field
from typing import Optional
import uuid, time

class Order(BaseModel):
    order_id: str = Field(default_factory=lambda: f"order-{uuid.uuid4().hex[:8]}")
    user_id: str
    goods_id: str
    num: int = 1
    amount: float = 0.0
    status: str = "PENDING"
    created_at: int = Field(default_factory=lambda: int(time.time()))

class OrderBuilder:
    """Builder：逐字段构造，返回可复用的构造器。"""
    def __init__(self, defaults: dict | None = None):
        self._defaults = defaults or {}

    def normal_order(self, user_id: str, goods_id: str = "g_1001", num: int = 1) -> dict:
        return Order(user_id=user_id, goods_id=goods_id, num=num, amount=19.9*num).model_dump()

    def edge_order(self, **overrides) -> dict:
        base = self.normal_order("u_normal")
        base.update(overrides)
        return base

    def with_amount(self, amount: float) -> dict:
        o = self.normal_order("u_normal")
        o["amount"] = amount
        return o
```

```python
# project/datafactory/factory.py
class DataFactory:
    """Factory：业务语义入口，调用 Builder + Provider。"""
    def __init__(self, provider: "DataProvider"):
        self._provider = provider
        self._builder = OrderBuilder()

    def normal_order(self, user_id: str | None = None) -> dict:
        uid = user_id or self._provider.pool("users").take_unique()
        return self._builder.normal_order(uid)

    def batch_orders(self, n: int, user_pool: str = "users") -> list[dict]:
        return [self.normal_order(self._provider.pool(user_pool).take_unique()) for _ in range(n)]

    def edge_orders(self) -> list[dict]:
        """边界/异常变体：num=0、num=99999、goods 不存在、无认证"""
        return [
            self._builder.edge_order(num=0),
            self._builder.edge_order(num=99999),
            self._builder.edge_order(goods_id="g_404"),
            self._builder.edge_order(user_id=None),  # 触发 401
        ]
```

```python
# project/datafactory/provider.py
import threading, time
from typing import Any, Optional

class DataPoolExhausted(Exception):
    pass

class DataPool:
    """数据池：内存存储 + 唯一性取用 + 标记已用。"""
    def __init__(self, data: list[dict], unique_key: str):
        self._data = data
        self._key = unique_key
        self._used = set()
        self._lock = threading.Lock()

    def take_unique(self) -> str:
        with self._lock:
            for item in self._data:
                key = item[self._key]
                if key not in self._used:
                    self._used.add(key)
                    return key
            raise DataPoolExhausted(f"池 {self._key} 耗尽")

    def mark_used(self, key: str) -> None:
        with self._lock:
            self._used.add(key)

    def available(self) -> int:
        return len(self._data) - len(self._used)

class DataProvider:
    """Provider：多数据池管理 + CSV 加载 + TTL 清理。"""
    def __init__(self):
        self._pools: dict[str, DataPool] = {}
        self._ttl_cleaner = TTLCleaner()

    @classmethod
    def from_csv(cls, csv_dir: str) -> "DataProvider":
        """从目录加载所有 *.csv，文件名作池名，首行作字段。"""
        import csv, os
        inst = cls()
        for fname in os.listdir(csv_dir):
            if not fname.endswith(".csv"): continue
            pool_name = fname[:-4]
            with open(os.path.join(csv_dir, fname), encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
                key = rows[0].keys().__iter__().__next__() if rows else "id"
                inst._pools[pool_name] = DataPool(rows, key)
        return inst

    def pool(self, name: str) -> DataPool:
        if name not in self._pools:
            raise KeyError(f"池 {name} 不存在，现有: {list(self._pools.keys())}")
        return self._pools[name]

    def register_ttl(self, key: str) -> None:
        self._ttl_cleaner.register(key)

    def sweep_ttl(self) -> int:
        return self._ttl_cleaner.sweep()

class TTLCleaner:
    def __init__(self, ttl: int = 3600):
        self._ttl = ttl
        self._records: list[tuple[str, float]] = []

    def register(self, key: str) -> None:
        self._records.append((key, time.time()))

    def sweep(self) -> int:
        now = time.time()
        keep, removed = [], 0
        for key, ts in self._records:
            if now - ts < self._ttl:
                keep.append((key, ts))
            else:
                removed += 1
        self._records = keep
        return removed
```

### 4.2 提取器（JSONPath / 正则 / Schema）

```python
# project/datafactory/extractors.py
import jsonpath_ng, re, json, jsonschema

def extract(path: str, source: dict, method: str = "jsonpath") -> str:
    if method == "jsonpath":
        matches = [m.value for m in jsonpath_ng.parse(path).find(source)]
        if not matches: raise ValueError(f"JSONPath {path} 未匹配")
        return str(matches[0])
    if method == "regex":
        m = re.search(path, json.dumps(source, ensure_ascii=False))
        if not m: raise ValueError(f"Regex {path} 未匹配")
        return m.group(1)
    if method == "schema":
        # 从 Schema 取示例值（略）
        return "example_value"
    raise ValueError(f"unknown method: {method}")
```

| 提取器 | 适用 | 例子 |
|--------|------|------|
| JSONPath | JSON 结构响应 | `$.data.token`、`$.data.orders[*].order_id` |
| 正则 | 文本/日志/响应体原始串 | `"token":"(.+?)"` |
| Schema | 从接口契约取字段示例 | 生成边界/缺省测试数据 |

### 4.3 隔离与清理（池/事务/软删/TTL）

```python
# 并发取数互不冲突
uid = provider.pool("users").take_unique()  # 并发 50 线程各取唯一 user_id

# TTL 清理
provider.register_ttl("order-123")
provider.sweep_ttl()  # 定时调用，返回清扫计数
```

**四条策略叠加使用**：
| 策略 | 做法 | 适用 | 成本 |
|------|------|------|------|
| **数据池隔离** | 每用例/线程从池取独立数据，用完标记 | 无状态接口、并发 | 低 |
| **事务回滚** | 用例在事务内执行，结束回滚 | 数据库直连造数 | 中 |
| **软删除** | 数据加 `deleted_at` 标记，不物理删除 | 线上/共享环境 | 低 |
| **TTL 清理** | 造数数据带过期时间，定时清扫 | 长时/批量造数 | 中 |

### 4.4 血缘、质量、目录、脱敏

```python
# bloodline: 每条造数记录自动写入血缘表
# source(UI/CSV/API) → transform(Builder/Factory/Extractor) → sink(Provider/DSL/Perf)

# quality gate: CI 门禁四维度
# 完整性 ≥99.9% | 唯一性 0 冲突 | 及时性 <24h | 准确性 100%

# catalog.json: Provider 启动自动扫描 → 字段名/类型/示例值/来源/更新时间

# masking: 手机/身份证/邮箱自动脱敏
MASK_RULES = {
    "phone": lambda v: v[:3] + "****" + v[-4:],
    "id_card": lambda v: v[:2] + "***********" + v[-1:],
    "email": lambda v: v.split("@")[0][:2] + "***@" + v.split("@")[1],
}
```

---

## 5. 输出契约（Output Contract）

| 产物 | 说明 |
|---|---|
| `project/datafactory/` | builder.py / factory.py / provider.py / extractors.py / quality.py / masking.py |
| 运行证明 | `pytest tests/test_data_factory.py -v` 全绿 |
| 血缘表 | `lineage_log` 可反向追溯任一造数记录 |
| 质量门禁 | `QualityGate.check()` 返回四维度指标，CI 门禁阈值化 |
| `catalog.json` | 字段名/类型/示例值/来源/更新时间，覆盖 100% |
| 脱敏数据 | 手机/身份证/邮箱自动脱敏，原文不入库 |

**验收前必须能当面演示**：
```bash
cd project
pytest tests/test_data_factory.py -v
# test_builder_chain PASSED
# test_factory_normal_order PASSED
# test_provider_uniqueness_and_exhaustion PASSED
# test_extract_jsonpath_and_regex PASSED
# test_schema_example PASSED
# test_ttl_cleaner PASSED
```

---

## 6. 验收清单（Acceptance Checklist）

- [ ] `OrderBuilder.normal_order()` 返回合法订单结构
- [ ] `DataFactory.normal_order()` 调用 Builder + Provider，返回合法订单
- [ ] `DataProvider.from_csv("data")` 正确加载第 2 章 CSV 文件
- [ ] `provider.pool("users").take_unique()` 并发 50 线程取唯一用户无重复
- [ ] 池耗尽抛 `DataPoolExhausted` 而非返回脏数据
- [ ] `DataFactory.batch_orders(n=10000)` 批量造数可补足性能层大规模数据缺口
- [ ] JSONPath/正则/Schema 三种提取器可提取 token/orderId
- [ ] `TTLCleaner.sweep()` 清扫过期记录并返回移除计数
- [ ] `QualityGate.check()` 四维度指标达标（完整性≥99.9%/唯一性 0 冲突/及时性<24h/准确性 100%）
- [ ] `catalog.json` 自动生成覆盖 100% 字段
- [ ] 脱敏规则对手机/身份证/邮箱生效、原文不入库

---

## 7. 常见坑点（Pitfalls）

| 现象 | 原因 | 排查 |
|---|---|---|
| 并发取数重复 | 未用锁 / 池数据未标记已用 | `DataPool._lock` 互斥 + `_used` 集合标记 |
| 提取器返回空串 | JSONPath/正则未匹配、未抛异常 | `extract()` 显式抛 `ValueError` 而非返回空串 |
| TTL 清理不生效 | 未定时调用 `sweep()` / 记录未注册 | 调用 `provider.register_ttl(key)`；定时任务跑 `sweep()` |
| 脱敏不生效 | 规则表缺键 / 脱敏在入库后 | `MASK_RULES` 全量覆盖；入库前调用 `mask(row)` |
| 血缘丢失 | 未在造数入口写血缘 | `lineage_log` 写入与造数同步、同事务 |

---

## 8. 能力等级（L1-L4）

| 等级 | 表现 |
|---|---|
| L1 | 能跑通 `OrderBuilder` + `DataFactory.normal_order()` + `DataProvider.from_csv()`，跑通单元测试 |
| L2 | 能补全 `DataPool` 唯一性取用、TTL 清理、JSONPath/正则/Schema 三种提取器、批量造数接口 |
| L3 | 能设计血缘表/质量门禁/元数据目录/脱敏规则表、设计 Provider 插件化接入数据库/API、实现事务回滚/软删除 |
| L4 | 能沉淀企业级数据治理平台：血缘可视化、质量仪表盘、数据目录检索、脱敏策略可视化配置、跨域数据血缘追踪 |

---

## 9. 附：最小可运行示例

```bash
cd project
pytest tests/test_data_factory.py -v
# test_builder_chain PASSED
# test_factory_normal_order PASSED
# test_provider_uniqueness_and_exhaustion PASSED
# test_extract_jsonpath_and_regex PASSED
# test_schema_example PASSED
# test_ttl_cleaner PASSED
```

---

*参考：第 3 章 §3.3 业务参数数据工厂、project/datafactory/、project/tests/test_data_factory.py、Skill-16 多协议性能脚本构建（同模板）*