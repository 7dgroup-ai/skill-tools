# Locust 脚本目录

## 结构
```
locust/
├── locustfile.py          # 可运行骨架（HttpUser + on_start 登录 + task 权重）
├── lib/
│   └── flow_common.py     # 公共步骤函数
└── data/
    ├── users.csv          # 用户池
    └── goods.csv          # 商品池
```

## 运行
```bash
# 冒烟
locust -f locustfile.py --host=http://localhost:8000 --users 1 --run-time 10s --headless

# 基准场景
cd ../scenarios && ./run_scenario.sh baseline.yaml
```

## 关键特性
- **on_start 登录**：每用户启动时登录一次，token 复用
- **task 权重**：goods_list(1) / add_cart(2) / cart_list(1) / order_preview(1) / order_create(1) / order_pay(1) / order_query(1)
- **数据池**：模块级加载 CSV，随机选择用户/商品
- **断言**：最终订单状态必须 `PAID`
- **幂等号**：`pay-{random}-{random}`