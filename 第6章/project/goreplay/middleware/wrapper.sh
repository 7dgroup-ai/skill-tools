#!/bin/bash
# project/goreplay/middleware/wrapper.sh
# 中间件启动封装：DEBUG 落 stderr，不污染 STDOUT 管道

set -euo pipefail

# 设置 Go 模块代理（国内环境）
export GOPROXY=https://goproxy.cn,direct

# 运行中间件
# 2>&1 将 stderr 重定向到 stdout，再通过 grep 过滤空行
# 但注意：中间件协议要求 STDIN/STDOUT 纯数据流，DEBUG 必须走 stderr
# 这里直接运行，DEBUG 由 token_modifier.go 内部通过 os.Stderr 输出
exec go run token_modifier.go