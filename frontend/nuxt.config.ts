export default defineNuxtConfig({
  ssr: false,
  devtools: { enabled: false },
  devServer: { port: 3004 },
  modules: ['@nuxt/ui'],
  css: ['~/assets/css/main.css'],
  colorMode: { preference: 'light' },
  app: {
    baseURL: '/',
    head: {
      title: 'DevTrack - 项目管理平台',
    },
  },
  routeRules: {
    '/api/**': { proxy: 'http://localhost:8000/api/**' },
  },
  compatibilityDate: '2025-01-01',
})
