# project/ — 第 5 章 准备阶段（RESAR：R + E）工程预留

> **状态**：第一轮预留结构（骨架 + 占位 docstring，不写完整实现）。第二轮在本结构上做真实案例演练与数据补充。

## 工程结构

```
project/
├── README.md               # 本说明
├── business_model/         # §5.1 业务模型抽取与流量分布（业务模型表 + 假设/校准记录）
├── slo/                    # §5.1 SLI/SLO 文档模板 + 容量规划目标
├── seed_data/              # §5.2 铺底数据生成脚本（幂等、local/prod 两档）
├── baseline/               # §5.3 基准场景脚本 + 阶梯加压 + 资源基线记录
└── monitoring/             # §5.4 Prometheus/Grafana/Exporters/SkyWalking 配置与策略文档
```

## 环境门槛与减配 POC

- **完整环境**：本地 Docker + docker-compose，起 sketch-store（`docker-compose up -d`）+
  Prometheus + Grafana（`make monitor-up`）。
- **减配 POC**（第一轮即可演练）：本机 k6/JMeter 直压 sketch-store，业务模型取
  `DAU=1 万` 档（高峰约 14 TPS），即可验证"业务模型 → SLO → 基线 → 监控"闭环。
- **完整档（含 SkyWalking）**：需要 JVM 或 OTel 上报能力，见 `monitoring/` 占位说明。

## 第二轮真实案例演练计划

1. `business_model/`：按真实网关日志校准高峰集中系数 H 与接口权重 w_i，回填 5.1.1 表格。
2. `slo/`：落地 SLO 文档 + 错误预算燃尽记录，与监控告警阈值对齐。
3. `seed_data/`：`make seed` 生成生产档数据（商品 100 万/用户 10 万/订单 500 万），
   校验行数与体积；跑通 `make smoke`。
4. `baseline/`：真机跑通基准场景 + 5 档阶梯加压，记录极限 TPS 与资源基线，与容量目标对照。
5. `monitoring/`：导入 Grafana 压测看板、验证六类关键计数器 PromQL、演示一条计数器联动证据链。
