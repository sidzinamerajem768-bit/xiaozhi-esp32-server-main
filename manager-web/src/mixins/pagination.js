/**
 * 分页 mixin
 * 提供统一的分页逻辑（currentPage, pageSize, paginatedList 等）
 *
 * 使用方式：
 *   mixins: [paginationMixin],
 *   在组件中提供 this.listData（完整列表）即可自动获得分页能力
 */
export default {
  data() {
    return {
      currentPage: 1,
      pageSize: 10,
      pageSizeOptions: [10, 20, 50, 100]
    }
  },
  computed: {
    pageCount() {
      return Math.ceil(this.listData.length / this.pageSize) || 1
    },
    paginatedList() {
      const start = (this.currentPage - 1) * this.pageSize
      return this.listData.slice(start, start + this.pageSize)
    },
    visiblePages() {
      const pages = []
      const maxVisible = 5
      let start = Math.max(1, this.currentPage - 2)
      let end = Math.min(this.pageCount, start + maxVisible - 1)
      if (end - start + 1 < maxVisible) {
        start = Math.max(1, end - maxVisible + 1)
      }
      for (let i = start; i <= end; i++) {
        pages.push(i)
      }
      return pages
    }
  },
  methods: {
    handlePageSizeChange(val) {
      this.pageSize = val
      this.currentPage = 1
    },
    goFirst() { this.currentPage = 1 },
    goPrev() { if (this.currentPage > 1) this.currentPage-- },
    goNext() { if (this.currentPage < this.pageCount) this.currentPage++ },
    goToPage(page) { this.currentPage = page }
  }
}