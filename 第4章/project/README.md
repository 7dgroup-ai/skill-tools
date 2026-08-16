# 精准测试工程（第 4 章交付物·已实现）

> **状态**：第一轮为预留结构，现已完成第二轮真实案例演练——四个子包均可用，
> 以仓库内 **sketch-store** 为被测对象跑通验证（见下「验收对照」）。
> **技能归属**：Skill-09（精准选测）/ Skill-10（覆盖率采集）/ Skill-11（门禁看板）/ Skill-12（优先级排序）。

## 工程结构

```
project/
├── README.md                    # 本文件
├── Makefile                     # 统一采集入口（collect-all：多语言覆盖率落盘 build/coverage/）
├── requirements.txt             # 依赖：tree-sitter / tree-sitter-python / coverage / pytest / fastapi / httpx
├── selection/                   # Skill-09 精准选测
│   ├── ast_diff.py              #   git diff + tree-sitter 方法级变更分析 → build/method_changes.json ✅
│   └── recommender.py           #   impact_map 查询 + 静态兜底 + 冒烟集合并 → build/test_list.txt ✅
├── coverage/                    # Skill-10 多语言覆盖率统一采集
│   ├── merge_report.py          #   Cobertura XML 汇总 → summary.json（含未覆盖行清单）✅
│   └── impact_map.sql           #   用例-方法映射表结构（§4.1.2）
├── priority/                    # Skill-12 用例优先级排序
│   ├── scorer.py                #   三维因子评分 F/A/T（纯函数，权重环境变量可配）✅
│   └── runner.py                #   时间预算贪心分批 P0/P1/P2 → build/queue.json ✅
├── build/                       # 运行产物（.gitignore 忽略）
│   ├── test_list.txt            #   动态用例集
│   ├── queue.json / skipped.txt #   优先级队列 + 未执行清单（绝不静默丢弃）
│   └── coverage/*.xml           #   统一覆盖率产物
└── tests/                       # 单元测试（全绿）
    ├── test_sketch_api.py       #   8 步链路接口用例（冒烟集，供覆盖率采集）
    ├── test_ast_diff.py         #   parse_diff / method_changes 纯函数
    ├── test_priority.py         #   scorer / partition
    ├── test_merge_report.py     #   Cobertura XML 解析与汇总
    └── conftest.py
```

## 快速开始

```bash
# 0. 安装依赖（建议 venv）
pip install -r requirements.txt

# 1. 收集 sketch-store 覆盖率（8 步链路用例 → Cobertura XML）
make collect-python        # 实测行覆盖 89% / 分支 73%（红线：行 ≥ 60%）

# 2. 汇总为 summary.json
make merge                 # 输出全局 line_rate / branch_rate / 未覆盖行数

# 3. 单元测试全绿
make test-python           # 12 passed

# 4. 方法级变更分析演示（需 git 仓库有真实 diff）
#    在 sketch-store 或任意 Python 仓库改一个方法后：
python -m selection.ast_diff --repo <repo> --src app --base HEAD~1 --head HEAD --out build/method_changes.json
python -m selection.recommender --changes build/method_changes.json --impact-map build/impact_map.db --out build/test_list.txt

# 5. 优先级排序分批
python -m priority.runner --metrics build/test_metrics.json --time-budget 1800 --out build/queue.json
```

> **注意**：项目内 `coverage/` 子包会遮蔽 `coverage` 工具，`make collect-python` 用二进制入口
> 运行 `coverage run`（见 Makefile 注释）。

## 验收对照（正文 §4.1~§4.4 红线）

| 验收项 | 状态 | 实测 |
|--------|:---:|------|
| 方法级变更识别：只改 `cart_add` 方法体，仅命中该文件 1 个方法 | ✅ | `app/routes/cart.py::cart_add L11-29 lines=[20,21]`，无其他文件误报 |
| AST 分析 < 5s（≤10 万行） | ✅ | 单文件毫秒级 |
| 推荐召回：变更 `cart_add` → 命中 `test_cart_add_ok`/`test_cart_add_bad_num` | ✅ | 冒烟集（8 步链路）恒在兜底 |
| impact_map 过期清理机制 | ✅ | `expire_stale(days=N)` 删除过期映射 |
| 对 sketch-store 跑 8 步链路用例，行覆盖 ≥ 60% | ✅ | **89%**（分支 73%） |
| 统一 Cobertura XML → summary.json（含未覆盖行） | ✅ | `line_rate=0.859 branch_rate=0.731 un_covered=32` |
| 排序评分纯函数可单测回放、缺数据兜底不报错 | ✅ | `test_score_defaults_when_missing` 通过 |
| P0/P1/P2 分批 + skipped 显性上报 | ✅ | `build/queue.json` + `build/skipped.txt` |
| 全量回归耗时下降 ≥ 50% | ◐ | 选测集 < 全量集；需真实 CI 历史回放验证 |
| SonarQube 门禁 / PR 评论 / Grafana 趋势（P1/P2 阶段） | ○ | 依赖外部环境，见正文 §4.3 |

## 生产级差异（正文 §4.1.4）

演示级（本章）：单仓库、Python 单语言、静态分析、SQLite 映射表。
生产级需补：多语言 grammar 并行、动态插桩（覆盖反射/动态导入）、微服务分库映射、
全局唯一测试 ID、向量库语义兜底、增量覆盖率（SonarQube `sonar.new_code_period`）。