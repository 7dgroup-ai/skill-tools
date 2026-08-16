#!/usr/bin/env bash
# 冒烟：跑通 sketch-store 8 步链路并校验业务状态。
# 用法：bash scripts/smoke.sh [HOST]
set -euo pipefail

HOST="${1:-http://localhost:8000}"
USER="user00001"
PASS="pass00001"
PASS_HASH="$(python3 -c "import hashlib;print(hashlib.sha256('${PASS}'.encode()).hexdigest())")"

echo "== 1. health =="
curl -sf "$HOST/health" && echo

echo "== 2. 商品列表 =="
curl -sf "$HOST/api/goods/list?page=1&size=5" | python3 -c "import sys,json;d=json.load(sys.stdin);print('code=',d['code'],'total=',d['data']['total'])"

echo "== 3. 登录 =="
TOKEN="$(curl -sf -X POST "$HOST/api/login" -H 'Content-Type: application/json' \
  -d "{\"username\":\"$USER\",\"password\":\"$PASS\"}" | python3 -c "import sys,json;print(json.load(sys.stdin)['data']['token'])")"
echo "token ok"

AUTH="Authorization: Bearer $TOKEN"
CT='Content-Type: application/json'

echo "== 4. 加购 =="
curl -sf -X POST "$HOST/api/cart/add" -H "$CT" -H "$AUTH" -d '{"goods_id":1,"num":2}'
echo

echo "== 5. 查购物车 =="
curl -sf "$HOST/api/cart/list" -H "$AUTH"
echo

echo "== 6. 预览建单 =="
ORDER_ID="$(curl -sf -X POST "$HOST/api/order/preview" -H "$CT" -H "$AUTH" -d '{}' | python3 -c "import sys,json;print(json.load(sys.stdin)['data']['order_id'])")"
echo "order_id=$ORDER_ID"

echo "== 7. 正式建单 =="
curl -sf -X POST "$HOST/api/order/create" -H "$CT" -H "$AUTH" -d "{\"order_id\":\"$ORDER_ID\"}" >/dev/null
echo "created"

echo "== 8. 支付 =="
curl -sf -X POST "$HOST/api/order/pay" -H "$CT" -H "$AUTH" \
  -d "{\"order_id\":\"$ORDER_ID\",\"pay_type\":\"mock\",\"request_id\":\"smoke-$(date +%s)\"}"
echo

echo "== 9. 查单（断言 PAID）=="
STATUS="$(curl -sf "$HOST/api/order/$ORDER_ID" -H "$AUTH" | python3 -c "import sys,json;print(json.load(sys.stdin)['data']['status'])")"
echo "status=$STATUS"
[ "$STATUS" = "PAID" ] && echo "SMOKE PASS" || { echo "SMOKE FAIL"; exit 1; }