#!/bin/bash
# project/scenarios/run_scenario.sh
# 通用场景执行入口：解析 YAML → 注入外部变量 → 启动对应工具
# 用法：./run_scenario.sh <scenario.yaml>
# 示例：./run_scenario.sh baseline.yaml

set -euo pipefail

SCENARIO_FILE=${1:-baseline.yaml}
SCENARIO_DIR=$(dirname "$0")
PROJECT_ROOT=$(cd "$SCENARIO_DIR/.." && pwd)

# 解析 YAML（需要 yq：brew install yq / apt-get install yq）
if ! command -v yq &> /dev/null; then
    echo "ERROR: yq not found. Install: brew install yq / apt-get install yq"
    exit 1
fi

NAME=$(yq -r '.name' "$SCENARIO_FILE")
TYPE=$(yq -r '.type' "$SCENARIO_FILE")
TOOL=$(yq -r '.tool // "jmeter"' "$SCENARIO_FILE")
TARGET=$(yq -r '.target' "$SCENARIO_FILE")

echo "=== 场景执行: $NAME ($TYPE) ==="
echo "工具: $TOOL"
echo "目标脚本: $TARGET"

# 通用环境变量（可被场景 YAML 覆盖）
export HOST=${HOST:-http://localhost:8000}
export VUS=${VUS:-10}
export DURATION=${DURATION:-180s}

# 根据工具分发执行
case "$TOOL" in
  jmeter)
    JMX="$PROJECT_ROOT/jmeter/plan/${TARGET}.jmx"
    if [ ! -f "$JMX" ]; then
        echo "ERROR: JMX not found: $JMX"
        exit 1
    fi
    # 提取阶梯参数（简化：只取第一档）
    VUS=$(yq -r '.stages[0].vus // .vus' "$SCENARIO_FILE")
    RAMP=$(yq -r '.stages[0].ramp // .ramp // "30s"' "$SCENARIO_FILE")
    DURATION=$(yq -r '.stages[0].duration // .duration // "180s"' "$SCENARIO_FILE")
    RAMP_SEC=$(echo "$RAMP" | sed 's/s$//')
    DUR_SEC=$(echo "$DURATION" | sed 's/s$//')

    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    RESULT_DIR="$PROJECT_ROOT/results/${NAME}_${TIMESTAMP}"
    mkdir -p "$RESULT_DIR"

    echo "JMeter 执行: $JMX"
    echo "  VUs: $VUS, Ramp: ${RAMP_SEC}s, Duration: ${DUR_SEC}s"
    echo "  结果目录: $RESULT_DIR"

    jmeter -n -t "$JMX" \
      -Jhost="$HOST" \
      -Jvus="$VUS" \
      -Jramp="$RAMP_SEC" \
      -Jduration="$DUR_SEC" \
      -l "$RESULT_DIR/result.jtl" \
      -e -o "$RESULT_DIR/dashboard"
    ;;

  k6)
    JS="$PROJECT_ROOT/k6/${TARGET}.js"
    if [ ! -f "$JS" ]; then
        echo "ERROR: k6 script not found: $JS"
        exit 1
    fi

    echo "k6 执行: $JS"
    echo "  环境变量已注入: HOST=$HOST VUS=$VUS DURATION=$DURATION"

    k6 run --env HOST="$HOST" --env VUS="$VUS" --env DURATION="$DURATION" "$JS"
    ;;

  locust)
    PY="$PROJECT_ROOT/locust/locustfile.py"
    if [ ! -f "$PY" ]; then
        echo "ERROR: Locust script not found: $PY"
        exit 1
    fi

    # Locust 用 --users --run-time
    VUS_NUM=$(echo "$VUS" | sed 's/[^0-9]//g')
    DUR_NUM=$(echo "$DURATION" | sed 's/[^0-9]//g')

    echo "Locust 执行: $PY"
    echo "  Users: $VUS_NUM, Run-time: ${DUR_NUM}s"

    locust -f "$PY" --host="$HOST" --users "$VUS_NUM" --run-time "${DUR_NUM}s" --headless
    ;;

  goreplay)
    # GoReplay 场景单独处理（录制/回放）
    echo "GoReplay 场景请直接使用 goreplay/record.sh 或 goreplay/replay.sh"
    exit 0
    ;;

  *)
    echo "ERROR: Unknown tool: $TOOL"
    exit 1
    ;;
esac

echo "=== 场景 $NAME 执行完成 ==="