/**
 * 加载状态 mixin
 * 提供 loading 状态管理
 *
 * 使用方式：
 *   mixins: [loadingMixin],
 *   在异步操作前后调用 this.setLoading(true/false)
 */
export default {
  data() {
    return {
      loading: false
    }
  },
  methods: {
    setLoading(val) {
      this.loading = val
    },
    async withLoading(fn) {
      this.loading = true
      try {
        return await fn()
      } finally {
        this.loading = false
      }
    }
  }
}