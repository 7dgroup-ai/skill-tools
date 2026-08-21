// project/lib/k6/auth.js
// 登录 + token 关联复用函数

import http from 'k6/http';
import { check } from 'k6';

/**
 * 登录并返回 token
 * @param {string} baseUrl - 基础 URL
 * @param {string} username - 用户名
 * @param {string} password - 密码
 * @returns {string} token
 */
export function login(baseUrl, username, password) {
  const res = http.post(`${baseUrl}/api/login`,
    JSON.stringify({ username, password }),
    { headers: { 'Content-Type': 'application/json' } });
  check(res, { 'login code=0': (r) => r.json('code') === 0 });
  return res.json('data.token');
}

/**
 * 构建带 Authorization 的请求头
 * @param {string} token
 * @returns {Object}
 */
export function authHeaders(token) {
  return {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  };
}