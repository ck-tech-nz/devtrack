import { defineVitestConfig } from '@nuxt/test-utils/config'

// 默认 node 环境跑纯 TS 逻辑(utils),快且无需 Nuxt 运行时。
// 组件 / composable 测试在文件顶部加 `// @vitest-environment nuxt`
// 注解,即可切到 Nuxt 运行时(happy-dom)以支持自动导入、mountSuspended、
// mockNuxtImport 等。
export default defineVitestConfig({
  test: {
    include: ['tests/**/*.test.ts'],
    environmentOptions: {
      nuxt: {
        domEnvironment: 'happy-dom',
      },
    },
  },
})
