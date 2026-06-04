import { defineConfig } from 'vitest/config'

// 仅用于测试纯 TS 逻辑(utils),不加载 Nuxt 运行时
export default defineConfig({
  test: {
    environment: 'node',
    include: ['tests/**/*.test.ts'],
  },
})
