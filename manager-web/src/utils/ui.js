import { Message } from 'element-ui'
import router from '../router'
import { isNull } from './helpers'

/**
 * 显示顶部错误通知（红色）
 */
export function showDanger(msg) {
  if (isNull(msg)) return
  Message({ message: msg, type: 'error', showClose: true })
}

/**
 * 显示顶部警告通知（橙色）
 */
export function showWarning(msg) {
  if (isNull(msg)) return
  Message({ message: msg, type: 'warning', showClose: true })
}

/**
 * 显示顶部成功通知（绿色）
 */
export function showSuccess(msg) {
  Message({ message: msg, type: 'success', showClose: true })
}

/**
 * 页面跳转
 * @param {string} path 目标路径
 * @param {boolean} isReplace 是否 replace（默认 push）
 */
export function goToPage(path, isReplace) {
  if (isReplace) {
    router.replace(path)
  } else {
    router.push(path)
  }
}