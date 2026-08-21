# 第 6 章构建阶段脚本工程骨架

> **版本**：v1.0 | 2026-08-08 | 李文
> **对接应用**：sketch-store (`docker-compose up -d` → `http://localhost:8000`)
> **核心链路**：商品列表 → 登录取 token → 加购 → 查购物车 → 预览单 → 建单 → 支付 → 查单
> **关联点**：登录响应 `$.data.token`、预览响应 `$.data.order_id`

## 目录结构

```
project/
├── README.md                    # 本文件
├── jmeter/                      # JMX 规划与提取器模板
│   ├── plan/
│   │   └── shopping_flow.jmx    # 主脚本（含 8 步链路 + 关联 + 断言 + 参数化）
│   ├── extractors/
│   │   ├── token_extractor.json    # JSON Extractor 预设：$.data.token → ${token}
│   │   └── orderId_extractor.json  # JSON Extractor 预设：$.data.order_id → ${orderId}
│   └── lib/
│       ├── common_headers.jmx      # 公共 Header: Content-Type, Accept-Encoding
│       └── csv_dataset_config.jmx  # CSV Data Set Config 模板
├── k6/                          # k6 脚本（JS + TS 契约）
│   ├── shopping_flow.js         # 可运行骨架（含关联、参数化、SLO 阈值）
│   ├── shopping_flow.ts         # TypeScript 接口契约（第二轮实现）
│   ├── lib/
│   │   ├── auth.js              # 登录 + token 关联复用函数
│   │   ├── data.js              # 数据池读取封装
│   │   └── utils.js             # 时间戳/随机数/UUID/幂等号生成
│   └── data/
│       ├── users.json           # 用户池（SharedArray 格式）
│       └── goods.json           # 商品池（SharedArray 格式）
├── locust/                      # Locust 脚本
│   ├── locustfile.py            # 可运行骨架（HttpUser + on_start 登录 + task 权重）
│   └── lib/
│       └── flow_common.py       # 公共步骤函数
├── goreplay/                    # GoReplay 录制回放
│   ├── record.sh                # 录制命令模板（含标记注入、gzip 分片、排除健康检查）
│   ├── replay.sh                # 回放命令模板（含中间件挂载、多 worker、统计）
│   ├── middleware/
│   │   ├── token_modifier.go    # token 关联中间件（双 Map 算法）
│   │   └── wrapper.sh           # 中间件启动封装
│   └── storage/
│       └── minio_upload.sh      # 流量文件上传 MinIO 脚本
├── data_pool/                   # 数据池生成器
│   ├── gen_users.py             # 生成 users.csv（含脱敏、分库分表分布模拟）
│   ├── gen_goods.py             # 生成 goods.csv（含库存、分类分布）
│   ├── seed.sql                 # 种子数据 SQL（配合 `make seed N=2400` 扩量）
│   └── csv_templates/
│       ├── users.csv.template   # 表头：userId,password
│       └── goods.csv.template   # 表头：goodsId
├── scenarios/                   # 场景声明（YAML + 执行脚本）
│   ├── baseline.yaml            # 基准场景（单接口阶梯）
│   ├── capacity.yaml            # 容量场景（全业务混合阶梯）
│   ├── stability.yaml           # 稳定性场景（最大稳定 TPS 持续）
│   ├── abnormal.yaml            # 异常场景（50% 背景 + 故障注入）
│   ├── stress.yaml              # 压力场景（专项：超限验证保护）
│   ├── config.yaml              # 配置场景（专项：调优前后对比）
│   ├── manifest.yaml            # 场景↔脚本映射登记
│   └── run_scenario.sh          # 通用执行入口（注入 -J/-e 变量）
├── lib/                         # 跨工具公共库
│   ├── jmeter/
│   │   ├── common_headers.jmx
│   │   └── extractor_presets.json
│   ├── k6/
│   │   ├── auth.js
│   │   ├── data.js
│   │   └── utils.js
│   └── python/
│       └── flow_common.py
├── projects/                    # 业务域脚本（版本化）
│   ├── order_flow/
│   │   ├── shopping_flow_v1.0.0.jmx
│   │   └── data/
│   │       ├── users.csv
│   │       └── goods.csv
│   └── user_center/
│       └── login_load_v1.0.0.jmx
└── baselines/                   # 基线记录（每次基准结果+阈值）
    └── baseline_20260804_1030/
        ├── result.jtl
        ├── dashboard/
        └── thresholds.json
```

## 运行前提

1. **启动被测应用**：
   ```bash
   cd /path/to/sketch-store
   docker-compose up -d
   make seed          # 铺底 1000 商品 / 500 用户
   make smoke         # 验通 8 步链路
   ```

2. **工具版本**：
   - JMeter 5.6+（推荐 HttpClient4 实现）
   - k6 v0.50+
   - Locust 2.15+
   - GoReplay 1.3.0 + Go 1.15+ + libpcap

3. **环境变量注入**（所有场景零改动跑通）：
   ```bash
   export HOST=http://localhost:8000
   export VUS=10
   export DURATION=180s
   ```

## 快速验证

```bash
# JMeter 冒烟（1 线程 1 迭代）
jmeter -n -t jmeter/plan/shopping_flow.jmx -Jhost=$HOST -Jvus=1 -Jduration=10 -l /tmp/smoke.jtl

# k6 冒烟
k6 run --env HOST=$HOST --env VUS=1 --env DURATION=10s k6/shopping_flow.js

# Locust 冒烟
locust -f locust/locustfile.py --host=$HOST --users 1 --run-time 10s --headless

# GoReplay 录制 60 秒验证
cd goreplay && ./record.sh  # 产出 request-mall-2026-08-08-10.gor
./replay.sh                 # 回放验证 token 关联
```

## 第二轮真实案例演练计划

| 轮次 | 目标 | 交付物 | 验收标准 |
|------|------|--------|----------|
| 1 | 单线程全绿 | 8 步链路 JMX/JS/PY + 关联/断言/参数化 | `status==PAID`、错误率 0% |
| 2 | 10 线程 3 分钟 | CSV 数据池 + 场景声明 + 基线 | 错误率 < 1%、无幂等冲突 |
| 3 | 容量阶梯拐点 | 容量场景报告 + 拐点定位 | 突破 SLO 即记拐点（p95>500ms/错误率>0.5%） |
| 4 | 稳定性 2.3 天 | 内存/连接/错误累积曲线 | 0 重启、内存不线性增长 |
| 5 | 异常注入恢复 | 故障注入脚本 + 恢复时间 | 5 min 内指标回基线 |

## 脚本市场元数据规范

每个脚本必须包含 `manifest.yaml` 条目：
```yaml
- name: order_flow_shopping_k6_v1.0.0.js
  domain: order
  protocol: [http]
  tool: k6
  business: "商品列表→登录→加购→查车→预览→建单→支付→查单"
  data_deps: [users.csv, goods.csv]
  owner: liwen
  version: 1.0.0
  acceptance: "单线程全绿 / 10线程3分钟错误率<1% / request_id 无幂等冲突"
  trust_level: "开箱可复现（需 sketch-store docker-compose up -d）"
```

## 三版对齐校验（CI 集成点）

| 版本 | 来源 | 校验规则 |
|------|------|----------|
| 脚本版本 | Git tag / 文件名 `v1.0.0` | `manifest.yaml` version 字段一致 |
| 数据版本 | `data_pool/seed.sql` + CSV 头注释 `# version: 20260804` | 运行前校验数据行数 ≥ 公式估算值 |
| 系统版本 | `docker-compose.yml` image tag / `make version` | 报告目录 `results/20260804_1030_baseline/` 含系统版本 |