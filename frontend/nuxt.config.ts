export default defineNuxtConfig({
  ssr: false,
  devtools: { enabled: false },
  devServer: { port: 3004 },
  modules: ['@nuxt/ui'],
  colorMode: { preference: 'light' },
  app: {
    baseURL: '/',
    head: {
      title: 'DevTrack - 项目管理平台',
      link: [
        {
          rel: 'stylesheet',
          href: 'https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap',
        },
      ],
    },
  },
  compatibilityDate: '2025-01-01',
})
