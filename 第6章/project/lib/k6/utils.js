// project/lib/k6/utils.js
// 时间戳/随机数/UUID/幂等号生成工具函数

/**
 * 当前时间戳（毫秒）
 * @returns {number}
 */
export function now() {
  return Date.now();
}

/**
 * 格式化时间戳
 * @param {string} format - 格式：yyyyMMddHHmmssSSS 等
 * @returns {string}
 */
export function formatTime(format) {
  const d = new Date();
  const pad = (n, w) => String(n).padStart(w, '0');
  return format
    .replace('yyyy', d.getFullYear())
    .replace('MM', pad(d.getMonth() + 1, 2))
    .replace('dd', pad(d.getDate(), 2))
    .replace('HH', pad(d.getHours(), 2))
    .replace('mm', pad(d.getMinutes(), 2))
    .replace('ss', pad(d.getSeconds(), 2))
    .replace('SSS', pad(d.getMilliseconds(), 3));
}

/**
 * 随机整数 [min, max]
 * @param {number} min
 * @param {number} max
 * @returns {number}
 */
export function randomInt(min, max) {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

/**
 * UUID v4
 * @returns {string}
 */
export function uuid() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
    const r = Math.random() * 16 | 0;
    const v = c === 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
}

/**
 * 幂等请求号：前缀 + VU + 时间戳 + 随机
 * @param {string} prefix
 * @returns {string}
 */
export function idempotentKey(prefix = 'req') {
  return `${prefix}-${__VU}-${Date.now()}-${randomInt(1000, 9999)}`;
}

/**
 * 计数器（跨 VU 共享，需配合 SharedArray 或外部存储）
 * 简单实现：基于 VU + 迭代次数
 * @param {string} prefix
 * @returns {string}
 */
export function counter(prefix = 'cnt') {
  return `${prefix}-${__VU}-${__ITER}`;
}