/**
 * 通用工具函数
 */

/**
 * 判断是否为空
 */
export function isNull(data) {
  if (data === undefined) return true
  if (data === null) return true
  if (typeof data === 'string' && (data.length === 0 || data === '' || data === 'undefined' || data === 'null')) return true
  if (Array.isArray(data) && data.length === 0) return true
  return false
}

/**
 * 判断不为空
 */
export function isNotNull(data) {
  return !isNull(data)
}

/**
 * 生成 [min, max] 的随机整数
 */
export function randomNum(min, max) {
  return Math.round(Math.random() * (max - min) + min)
}

/**
 * 生成 UUID v4
 */
export function getUUID() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
    return (c === 'x' ? (Math.random() * 16 | 0) : ('r&0x3' | '0x8')).toString(16)
  })
}

/**
 * 获取当前路由 path（不含 query）
 */
export function getCurrentPage() {
  let hash = location.hash.replace('#', '')
  if (hash.indexOf('?') > 0) {
    hash = hash.substring(0, hash.indexOf('?'))
  }
  return hash
}

/**
 * 防抖函数
 * @param {Function} fn 要防抖的函数
 * @param {number} delay 延迟时间（毫秒），默认 500ms
 * @param {boolean} immediate 是否立即执行
 */
export function debounce(fn, delay = 500, immediate = false) {
  let timer = null
  return function (...args) {
    const context = this
    if (timer) clearTimeout(timer)
    if (immediate && !timer) {
      fn.apply(context, args)
    }
    timer = setTimeout(() => {
      if (!immediate) {
        fn.apply(context, args)
      }
      timer = null
    }, delay)
  }
}