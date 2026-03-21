declare const process: { env: Record<string, string | undefined> }
const apiBase = process.env.NUXT_API_BASE || 'http://localhost:8000'

export default defineNuxtConfig({
  ssr: false,
  devtools: { enabled: false },
  devServer: { port: 3004 },
  modules: ['@nuxt/ui'],
  css: ['~/assets/css/main.css'],
  colorMode: { preference: 'light', fallback: 'light' },
  app: {
    baseURL: '/',
    head: {
      title: 'DevTrack - 项目管理平台',
    },
  },
  routeRules: {
    '/api/**': { proxy: `${apiBase}/api/**` },
  },
  nitro: {
    devProxy: {
      '/api/': {
        target: `${apiBase}/api/`,
        changeOrigin: true,
      },
    },
  },
  compatibilityDate: '2025-01-01',
})
