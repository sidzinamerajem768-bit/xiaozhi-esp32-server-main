/**
 * 表格选择 mixin
 * 提供表格多选逻辑
 *
 * 使用方式：
 *   mixins: [selectionMixin],
 *   表格数据每行需有 selected 字段
 */
export default {
  methods: {
    /**
     * 全选/取消全选当前页
     */
    toggleSelectAll(list) {
      const shouldSelect = !this.isAllSelected(list)
      list.forEach(row => { row.selected = shouldSelect })
    },
    /**
     * 判断当前页是否全选
     */
    isAllSelected(list) {
      return list.length > 0 && list.every(item => item.selected)
    },
    /**
     * 获取已选中的行
     */
    getSelected(list) {
      return list.filter(item => item.selected)
    }
  }
}