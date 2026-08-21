"""monitoring/ —— §5.4 全链路监控体系（占位模块）。

第二轮真实案例演练：
- prometheus.yml       : scrape_configs（node/app/mysql/redis exporter）
- dashboards/*.json    : Grafana 压测看板（吞吐/p95/错误率/资源，带阈值红线）
- alerts/*.rules       : 六类关键计数器告警规则（GC/线程池/连接池/慢查询/队列/链路）
- skywalking/          : OAP + UI + Agent 部署说明（JVM/OTel）
- strategy.md          : 全局与定向监控策略 + "全局→定向→根因→回验"路径
"""
