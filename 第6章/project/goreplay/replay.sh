#!/bin/bash
# project/goreplay/replay.sh
# GoReplay 回放脚本：挂载中间件、多 worker、统计、熔断
# 用法：./replay.sh [input_file] [target_url]
# 示例：./replay.sh ./traffic/request-mall-2026-08-08-10.gz http://staging.target:8000

set -euo pipefail

INPUT_FILE=${1:-./traffic/request-mall-2026-08-08-10.gz}
TARGET_URL=${2:-http://localhost:8000}
WORKERS=${GOR_WORKERS:-8}
MIDDLEWARE=${MIDDLEWARE:-./middleware/wrapper.sh}
LOOP=${GOR_LOOP:-true}

echo "=== GoReplay 回放启动 ==="
echo "输入文件: $INPUT_FILE"
echo "目标地址: $TARGET_URL"
echo "Worker 数: $WORKERS"
echo "中间件: $MIDDLEWARE"
echo "循环回放: $LOOP"

LOOP_FLAG=""
if [ "$LOOP" = "true" ]; then
  LOOP_FLAG="--input-file-loop"
fi

sudo ./goreplay \
  --input-file="$INPUT_FILE" \
  $LOOP_FLAG \
  --output-http="$TARGET_URL" \
  --middleware="$MIDDLEWARE" \
  --prettify-http \
  --output-http-track-response \
  --output-http-workers "$WORKERS" \
  --split-output true \
  --stats \
  --output-http-timeout 30s