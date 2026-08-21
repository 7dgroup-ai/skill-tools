# GoReplay 录制回放目录

## 结构
```
goreplay/
├── record.sh              # 录制命令模板
├── replay.sh              # 回放命令模板
├── middleware/
│   ├── token_modifier.go  # token 关联中间件（双 Map 算法）
│   └── wrapper.sh         # 中间件启动封装
└── storage/
    └── minio_upload.sh    # 流量文件上传 MinIO（第二轮实现）
```

## 录制
```bash
# 录制 1 小时，输出按小时切片 gzip
./record.sh 3600 request-mall
# 产出：traffic/request-mall-2026-08-08-10.gz
```

## 回放
```bash
# 挂载中间件、8 worker、循环回放、统计
./replay.sh traffic/request-mall-2026-08-08-10.gz http://staging.target:8000
```

## 中间件核心逻辑（token_modifier.go）
- **Payload Type 1 (Request)**：非登录请求 → 读 Header `token` → 查 `tokenAliases[old]` → 替换为新 token
- **Payload Type 2 (Original Response)**：登录响应 → 解析 `Body.data.token` → `originalTokens[reqID] = token`
- **Payload Type 3 (Replayed Response)**：登录回放响应 → 解析 `Body.data.token` → `tokenAliases[originalToken] = newToken`

## 关键参数
| 参数 | 说明 |
|------|------|
| `--input-raw :8201` | 监听网关端口（需 root） |
| `--input-raw-track-response` | 采集响应（关联前提） |
| `--http-set-header dunshan:7DGroup` | 注入压测标记（全链路隔离） |
| `--prettify-http` | 自动解码 gzip/chunked |
| `--middleware ./wrapper.sh` | 挂载 token 关联中间件 |
| `--output-http-workers 8` | 8 并发 worker |
| `--split-output true` | 单连接拆分防限流 |
| `--stats` | 每 5s 吞吐统计 |