// sketch-store 8 步链路压测脚本（对齐全书 Skill-16 关联/参数化）
// 数据池: data/users.json, data/goods.json（由 make seed 或 loadtest/gen_data.py 生成）
// 运行: k6 run --env HOST=http://localhost:8000 --env VUS=10 --env DURATION=180s shopping_flow.js
import http from 'k6/http';
import { check, sleep } from 'k6';
import { SharedArray } from 'k6/data';

const BASE = __ENV.HOST || 'http://localhost:8000';

export const options = {
  vus: parseInt(__ENV.VUS) || 10,
  duration: __ENV.DURATION || '180s',
  thresholds: {
    http_req_failed: ['rate<0.01'],
    http_req_duration: ['p(95)<500'],
    checks: ['rate>0.95'],
  },
};

const users = new SharedArray('users', () => JSON.parse(open('./data/users.json')));
const goods = new SharedArray('goods', () => JSON.parse(open('./data/goods.json')));

export default function () {
  // 1. 商品列表
  http.get(`${BASE}/api/goods/list?page=1&size=20`);

  // 2. 登录取 token（关联）
  const u = users[__VU % users.length];
  const login = http.post(`${BASE}/api/login`,
    JSON.stringify({ username: u.username, password: u.password }),
    { headers: { 'Content-Type': 'application/json' } });
  const token = login.json('data.token');
  const auth = { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` };

  // 3. 加购（参数化：从商品池轮询）
  const g = goods[__VU % goods.length];
  http.post(`${BASE}/api/cart/add`, JSON.stringify({ goods_id: g.goods_id, num: 1 }), { headers: auth });

  // 4. 查购物车
  http.get(`${BASE}/api/cart/list`, { headers: auth });

  // 5. 预览单 → orderId（关联）
  const preview = http.post(`${BASE}/api/order/preview`, '{}', { headers: auth });
  const orderId = preview.json('data.order_id');

  // 6. 建单
  http.post(`${BASE}/api/order/create`, JSON.stringify({ order_id: orderId }), { headers: auth });

  // 7. 支付（幂等 request_id）
  http.post(`${BASE}/api/order/pay`, JSON.stringify({
    order_id: orderId, pay_type: 'mock', request_id: `pay-${__VU}-${Date.now()}`,
  }), { headers: auth });

  // 8. 查单（断言 PAID）
  const query = http.get(`${BASE}/api/order/${orderId}`, { headers: auth });
  check(query, { 'status=PAID': (r) => r.json('data.status') === 'PAID' });

  sleep(1);
}