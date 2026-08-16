# sketch-store

全书《技能栈下的非功能测试》的**共享被测应用**：轻量版电商链路（对齐《被测应用设计手稿》）。

## 业务链路（8 步）

| # | 业务块点 | 接口 | 说明 |
|---|---------|------|------|
| 1 | 商品列表 | `GET /api/goods/list?page=&size=` | 分页，`latency_sim` 可调慢 |
| 2 | 登录取 token | `POST /api/login` | 返回 JWT，做**关联**素材 |
| 3 | 加入购物车 | `POST /api/cart/add` | 需 token + goods_id + num |
| 4 | 查询购物车 | `GET /api/cart/list` | 汇总商品/金额 |
| 5 | 生成订单(预览) | `POST /api/order/preview` | 由购物车生成订单项 |
| 6 | 生成正式订单 | `POST /api/order/create` | 携带 order_id(关联) |
| 7 | 支付订单 | `POST /api/order/pay` | 模拟支付 + 延时，幂等 request_id |
| 8 | 查询订单 | `GET /api/order/{order_id}` | 断言校验落点 |

## 快速开始

```bash
# 1. 起服务（uvicorn，默认 8000）
make up            # 或 docker-compose up -d
# 2. 铺底数据（1000 商品 + 500 用户）
make seed
# 3. 冒烟跑通 8 步链路
make smoke
```

默认账号：`user00001` / `pass00001`

## 内置能力（全书各章引用）

- **`/metrics`**：Prometheus 文本指标（请求数/延迟/错误数 + 业务指标），配合 Skill-15/39。
- **`/openapi.json` + `/docs`**：FastAPI 自动生成，供 DAST/OpenAPI 驱动扫描（第 11 章）。
- **瓶颈注入开关**（`POST /api/switch`）：
  - `{"switch":"latency_sim","on":true}` — 慢查询注入（默认 800ms，可 `latency_ms` 调）
  - `{"switch":"cache_path","on":true}` — 商品列表走内存缓存
  - `{"switch":"sql_injection","on":false}` — 关闭登录接口的 SQL 注入演示点（**生产务必关闭**）
- **k6 压测脚本**：`loadtest/shopping_flow.js`（含关联/参数化/SLO 阈值），数据池见 `loadtest/gen_data.py`。

## 目录结构

```
sketch-store/
├── app/                 # FastAPI 应用（main/models/auth/metrics/latency_sim + routes/）
├── scripts/             # seed.py 铺底 / smoke.sh 冒烟
├── loadtest/            # k6 脚本 + 数据池生成器
├── chaos/               # 单机混沌实验 yaml
├── security/            # ZAP baseline 扫描脚本
├── Makefile             # 一键任务
├── docker-compose.yml / Dockerfile
└── requirements.txt
```

## 验收对照

- [x] `make up` + `/health` 返回 UP
- [x] `make seed` 生成 1000 商品 / 500 用户
- [x] `make smoke` 跑通 8 步链路且订单状态 = PAID
- [x] `/metrics` 输出 Prometheus 文本指标
- [x] 开关接口可注入/撤销瓶颈（latency_sim / cache_path / sql_injection）
- [ ] k6 脚本在装好 k6 后跑通（`k6 run loadtest/shopping_flow.js`）