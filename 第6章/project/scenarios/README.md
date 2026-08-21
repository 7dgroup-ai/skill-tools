# 场景声明目录

## 结构
```
scenarios/
├── baseline.yaml      # 基准：单接口阶梯
├── capacity.yaml      # 容量：全业务混合阶梯
├── stability.yaml     # 稳定性：最大稳定 TPS 持续
├── abnormal.yaml      # 异常：50% 背景 + 故障注入
├── stress.yaml        # 压力（专项）：超限验证保护
├── config.yaml        # 配置（专项）：调优前后对比
├── manifest.yaml      # 场景↔脚本映射登记
└── run_scenario.sh    # 通用执行入口
```

## 场景分类（RESAR 方法论）

| 类别 | 场景 | 目标 | 判定 |
|------|------|------|------|
| **核心四类** | baseline | 单接口最大 TPS + 基线 | 上一档=极限 TPS；p95 波动<±5% |
| | capacity | 系统整体最大容量 | 满足 SLO 的最大混合吞吐；突破 SLO 即拐点 |
| | stability | 长时暴露隐性瓶颈 | 0 错误、0 重启、内存不线性增长 |
| | abnormal | 故障注入验证恢复 | 5 min 内指标回基线（背景标准方差≤5%） |
| **专项** | stress | 超限验证保护机制 | 有保护生效且无雪崩 |
| | config | 调优前后对比 | 关键指标提升≥10% 且不回退 |

## 执行顺序铁律
```
baseline → capacity → (stability + abnormal) → [stress | config]
```

## 执行
```bash
# 所有场景零改动跑通（外部变量注入）
export HOST=http://localhost:8000
export VUS=10
export DURATION=180s

./run_scenario.sh baseline.yaml
./run_scenario.sh capacity.yaml
./run_scenario.sh stability.yaml
./run_scenario.sh abnormal.yaml
./run_scenario.sh stress.yaml
./run_scenario.sh config.yaml
```

## 场景模板字段（统一）
```yaml
name: baseline_shopping_flow
type: baseline                    # baseline/capacity/stability/abnormal/stress/config
target: shopping_flow             # 脚本资产名
protocol: http
stages: [...]                     # 阶梯定义
business_mix: {...}               # 业务比例（容量场景）
slo: {...}                        # 量化阈值
monitor: [...]                    # 监控面板绑定
pass_when: "一句话判定"
```