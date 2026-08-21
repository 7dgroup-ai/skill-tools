#!/bin/bash
# project/goreplay/record.sh
# GoReplay 录制脚本：网关端口抓包、注入压测标记、gzip 分片、排除健康检查
# 用法：./record.sh [duration_seconds] [output_prefix]
# 示例：./record.sh 3600 request-mall

set -euo pipefail

DURATION=${1:-3600}
PREFIX=${2:-request-mall}
PORT=${GATEWAY_PORT:-8201}
OUTPUT_DIR=${OUTPUT_DIR:-./traffic}
MARKER_KEY=${MARKER_KEY:-dunshan}
MARKER_VAL=${MARKER_VAL:-7DGroup}

mkdir -p "$OUTPUT_DIR"

echo "=== GoReplay 录制启动 ==="
echo "端口: $PORT"
echo "时长: ${DURATION}s"
echo "输出: $OUTPUT_DIR/${PREFIX}-%Y-%m-%d-%H.gz"
echo "压测标记: $MARKER_KEY: $MARKER_VAL"
echo "排除: /actuator/health"

# 需要 root 权限监听网卡
sudo nohup timeout "$DURATION" ./gor \
  --input-raw ":$PORT" \
  --output-file="$OUTPUT_DIR/${PREFIX}-%Y-%m-%d-%H.gz" \
  -output-file-append \
  --http-set-header "$MARKER_KEY:$MARKER_VAL" \
  --http-set-header "User-Agent:Replayed-by-Gor" \
  --input-raw-track-response \
  --prettify-http \
  --http-disallow-url "/actuator/health" \
  --stats \
  > "$OUTPUT_DIR/gor-record.log" 2>&1 &

PID=$!
echo "录制进程 PID: $PID"
echo "日志: tail -f $OUTPUT_DIR/gor-record.log"
echo "停止: kill $PID"

# 保存 PID 供后续停止
echo $PID > "$OUTPUT_DIR/gor-record.pid"