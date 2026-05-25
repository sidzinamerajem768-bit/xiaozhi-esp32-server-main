import Vue from 'vue'
import VueI18n from 'vue-i18n'
import zhCN from './zh_CN'

Vue.use(VueI18n)

const i18n = new VueI18n({
  locale: 'zh_CN',
  fallbackLocale: 'zh_CN',
  messages: { zh_CN: zhCN }
})

export default i18n