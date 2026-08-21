# k6 脚本目录

## 结构
```
k6/
├── shopping_flow.js       # 可运行骨架（关联、参数化、SLO 阈值）
├── shopping_flow.ts       # TypeScript 接口契约（第二轮实现）
├── lib/
│   ├── auth.js            # 登录 + token 关联复用函数
│   ├── data.js            # 数据池读取封装
│   └── utils.js           # 时间戳/随机数/UUID/幂等号生成
└── data/
    ├── users.json         # 用户池（SharedArray 格式）
    └── goods.json         # 商品池（SharedArray 格式）
```

## 运行
```bash
# 冒烟
k6 run --env HOST=http://localhost:8000 --env VUS=1 --env DURATION=10s shopping_flow.js

# 基准场景
cd ../scenarios && ./run_scenario.sh baseline.yaml
```

## 关键特性
- **SharedArray**：`users.json`/`goods.json` 仅加载一次，跨 VU 共享内存
- **关联**：`login.json('data.token')` → `authHeaders(token)` 注入下游
- **参数化**：`pickUser(users)` / `pickGoods(goods)` 轮询
- **SLO 阈值**：`http_req_failed < 1%`、`p(95) < 500ms`、`checks > 99%`
- **幂等号**：`pay-${__VU}-${Date.now()}`