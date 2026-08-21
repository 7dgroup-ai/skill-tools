# 数据池生成器目录

## 结构
```
data_pool/
├── gen_users.py             # 生成 users.csv
├── gen_goods.py             # 生成 goods.csv
├── seed.sql                 # 种子数据 SQL（配合 make seed）
├── csv_templates/
│   ├── users.csv.template   # 表头：userId,password
│   └── goods.csv.template   # 表头：goodsId
└── README.md
```

## 生成命令
```bash
# 铺底数据（基准场景）
python3 gen_users.py --rows 500 --output ../jmeter/plan/data/users.csv
python3 gen_goods.py --rows 1000 --output ../jmeter/plan/data/goods.csv

# 容量场景（200 VU × 10 迭代 × 1.2 安全系数 = 2400 行）
python3 gen_users.py --rows 2400 --output ../jmeter/plan/data/users.csv
python3 gen_goods.py --rows 2400 --output ../jmeter/plan/data/goods.csv
```

## 三类数据池（§6.2.2）

| 类型 | 文件 | 消费方式 | 场景 |
|------|------|----------|------|
| 静态字典池 | users.csv | CSV 轮询 | 登录账号、基础信息 |
| 静态字典池 | goods.csv | CSV 轮询 | 商品基础信息 |
| 唯一流水池 | 运行时生成 | `${__time}`/`${__UUID}`/`idempotentKey` | 订单号、幂等号 |
| 关联衍生池 | 运行时提取 | JSON Extractor / `login.json()` | token、orderId |

## 数据量公式
```
最低行数 = VU数 × 单VU消费次数 × 安全系数(≥1.2)
例：200 VU × 10 迭代 × 1.2 = 2400 行
```

## 数据来源分级
| 来源 | 类型 | 适用 |
|------|------|------|
| 生产脱敏 | 死水 | 登录账号、商品基础信息 |
| 接口造数 | 活水 | 订单号、支付流水 |
| 运行时函数 | 活水 | 时间戳、UUID、随机数 |

## 直方图校验（防缓存命中率虚高）
```sql
-- 客户流水记录数分布
SELECT customer_id, COUNT(*) AS txn_count
FROM customer_transactions
GROUP BY customer_id
ORDER BY txn_count DESC;
-- 合理：100~200 条/客户
-- 异常：头部 69,865 条 → 过滤或重造
```

## 三级兜底（数据不足时）
1. **扩量铺底** `make seed N=2400` → 最真实
2. **动态生成** 前缀+时间戳+随机 → 无上限
3. **允许轮询+标注失真** → 仅基准/冒烟可用，**禁用于容量/稳定性**