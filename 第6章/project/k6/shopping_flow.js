// project/k6/shopping_flow.js
// sketch-store 8 步链路：商品列表→登录→加购→查车→预览→建单→支付→查单
// 关联：token、orderId | 参数化：users.json、goods.json | SLO 阈值内置
// 运行：k6 run --env HOST=http://localhost:8000 --env VUS=10 --env DURATION=180s shopping_flow.js

import http from 'k6/http';
import { check, sleep } from 'k6';
import { randomIntBetween } from 'https://jslib.k6.io/k6-utils/1.2.0/index.js';
import { SharedArray } from 'k6/data';

// ---------- 外部变量注入 ----------
const BASE = __ENV.HOST || 'http://localhost:8000';
export const options = {
  vus: parseInt(__ENV.VUS) || 10,
  duration: __ENV.DURATION || '180s',
  thresholds: {                    // SLO 先行：不达标即失败
    http_req_failed: ['rate<0.01'],
    http_req_duration: ['p(95)<500'],
    checks: ['rate>0.99'],
  },
};

// ---------- 数据池（SharedArray：跨 VU 共享内存，仅加载一次） ----------
const users = new SharedArray('users', () => JSON.parse(open('./data/users.json')));  // [{username,password},...]
const goods = new SharedArray('goods', () => JSON.parse(open('./data/goods.json')));   // [{goodsId},...]

// ---------- 主流程 ----------
export default function () {
  // 1. 商品列表
  const list = http.get(`${BASE}/api/goods/list?page=1&size=20`);
  check(list, { 'goods code=0': (r) => r.json('code') === 0 });

  // 2. 登录取 token（每 VU 独立用户，避免并发互踢/共享 token）
  const uid = __VU % users.length;
  const login = http.post(`${BASE}/api/login`,
    JSON.stringify({ username: users[uid].username, password: users[uid].password }),
    { headers: { 'Content-Type': 'application/json' } });
  check(login, { 'login code=0': (r) => r.json('code') === 0 });
  const token = login.json('data.token');                 // ① 关联：token

  // 注入下游 Authorization Header
  const auth = { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` };  // ② 注入

  // 3. 加购（从共享商品池轮询，避免同一 SKU 被抢光）
  const goodsId = goods[__VU % goods.length].goodsId;
  http.post(`${BASE}/api/cart/add`,
    JSON.stringify({ goods_id: goodsId, num: randomIntBetween(1, 5) }),
    { headers: auth });

  // 4. 查购物车
  http.get(`${BASE}/api/cart/list`, { headers: auth });

  // 5. 预览单 → 提取 orderId
  const preview = http.post(`${BASE}/api/order/preview`, '{}', { headers: auth });
  check(preview, { 'preview code=0': (r) => r.json('code') === 0 });
  const orderId = preview.json('data.order_id');          // ③ 关联：orderId

  // 6. 建单
  http.post(`${BASE}/api/order/create`,
    JSON.stringify({ order_id: orderId }), { headers: auth });

  // 7. 支付（幂等 request_id：VU + 时间戳）
  http.post(`${BASE}/api/order/pay`,
    JSON.stringify({
      order_id: orderId,
      pay_type: 'mock',
      request_id: `pay-${__VU}-${Date.now()}`
    }), { headers: auth });

  // 8. 查单（最终业务状态 PAID）
  const query = http.get(`${BASE}/api/order/${orderId}`, { headers: auth });
  check(query, { 'status=PAID': (r) => r.json('data.status') === 'PAID' });

  sleep(1);
}