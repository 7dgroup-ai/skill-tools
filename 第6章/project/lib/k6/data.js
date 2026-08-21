// project/lib/k6/data.js
// 数据池读取封装（SharedArray）

import { SharedArray } from 'k6/data';

/**
 * 加载用户池
 * @param {string} path - 相对路径（如 ./data/users.json）
 * @returns {SharedArray}
 */
export function loadUsers(path) {
  return new SharedArray('users', () => JSON.parse(open(path)));
}

/**
 * 加载商品池
 * @param {string} path - 相对路径（如 ./data/goods.json）
 * @returns {SharedArray}
 */
export function loadGoods(path) {
  return new SharedArray('goods', () => JSON.parse(open(path)));
}

/**
 * 按 VU 轮询取用户
 * @param {SharedArray} users
 * @returns {Object} {username, password}
 */
export function pickUser(users) {
  return users[__VU % users.length];
}

/**
 * 按 VU 轮询取商品
 * @param {SharedArray} goods
 * @returns {number} goodsId
 */
export function pickGoods(goods) {
  return goods[__VU % goods.length].goodsId;
}