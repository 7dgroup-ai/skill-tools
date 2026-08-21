# JMeter 脚本目录

## 结构
```
jmeter/
├── plan/
│   └── shopping_flow.jmx      # 主脚本（8 步链路 + 关联 + 断言 + 参数化）
├── extractors/
│   ├── token_extractor.json   # JSON Extractor 预设
│   └── orderId_extractor.json # JSON Extractor 预设
└── lib/
    ├── common_headers.jmx     # 公共 Header 片段
    └── csv_dataset_config.jmx # CSV Data Set Config 模板
```

## 运行
```bash
# 冒烟（1 线程 10 秒）
jmeter -n -t plan/shopping_flow.jmx -Jhost=http://localhost:8000 -Jvus=1 -Jduration=10 -l /tmp/smoke.jtl

# 基准场景（通过场景入口）
cd ../scenarios && ./run_scenario.sh baseline.yaml
```

## 关键配置点
- **线程组**：`${__P(vus,10)}` / `${__P(ramp,30)}` / `${__P(duration,180)}`
- **HTTP Defaults**：HttpClient4 + Keep-Alive + 分级超时
- **Header Manager**：Content-Type + Accept-Encoding + 压测标记 `dunshan:7DGroup`
- **Cookie Manager**：Policy=compatibility
- **CSV Data Set**：users.csv / goods.csv，Recycle=True, StopThread=False, Sharing=All
- **关联**：JSON Extractor `$.data.token` → `${token}`、`$.data.order_id` → `${orderId}`
- **断言**：每步 JSON Path `$.code == 0`，最终 `$.data.status == PAID`
- **幂等参数**：`pay-${__threadNum}-${__time(yyyyMMddHHmmssSSS)}`