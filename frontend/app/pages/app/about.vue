<template>
  <div class="space-y-6 max-w-2xl">
    <h1 class="text-2xl font-semibold text-gray-900 dark:text-gray-100">关于系统</h1>

    <template>
      <!-- 前端信息 -->
      <div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 p-6 space-y-4">
        <h2 class="text-base font-semibold text-gray-900 dark:text-gray-100">前端</h2>
        <dl class="grid grid-cols-[auto_1fr] gap-x-6 gap-y-2 text-sm">
          <dt class="text-gray-500 dark:text-gray-400">Git Hash</dt>
          <dd class="text-gray-900 dark:text-gray-100 font-mono">{{ runtimeConfig.gitHash || '—' }}</dd>
          <dt class="text-gray-500 dark:text-gray-400">构建时间</dt>
          <dd class="text-gray-900 dark:text-gray-100">{{ runtimeConfig.buildDate || '开发模式' }}</dd>
          <dt class="text-gray-500 dark:text-gray-400">Nuxt</dt>
          <dd class="text-gray-900 dark:text-gray-100 font-mono">{{ runtimeConfig.nuxtVersion }}</dd>
          <dt class="text-gray-500 dark:text-gray-400">Vue</dt>
          <dd class="text-gray-900 dark:text-gray-100 font-mono">{{ runtimeConfig.vueVersion }}</dd>
        </dl>
      </div>

      <!-- 后端信息 -->
      <div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 p-6 space-y-4">
        <h2 class="text-base font-semibold text-gray-900 dark:text-gray-100">后端</h2>
        <div v-if="loading" class="text-sm text-gray-400">加载中...</div>
        <div v-else-if="error" class="text-sm text-red-500">{{ error }}</div>
        <dl v-else-if="about" class="grid grid-cols-[auto_1fr] gap-x-6 gap-y-2 text-sm">
          <dt class="text-gray-500 dark:text-gray-400">版本</dt>
          <dd class="text-gray-900 dark:text-gray-100 font-mono">{{ about.backend.version }}</dd>
          <dt class="text-gray-500 dark:text-gray-400">Git Hash</dt>
          <dd class="text-gray-900 dark:text-gray-100 font-mono">{{ about.backend.git_hash || '—' }}</dd>
          <dt class="text-gray-500 dark:text-gray-400">构建时间</dt>
          <dd class="text-gray-900 dark:text-gray-100">{{ about.backend.build_date || '开发模式' }}</dd>
          <dt class="text-gray-500 dark:text-gray-400">Python</dt>
          <dd class="text-gray-900 dark:text-gray-100 font-mono">{{ about.backend.python_version }}</dd>
          <dt class="text-gray-500 dark:text-gray-400">Django</dt>
          <dd class="text-gray-900 dark:text-gray-100 font-mono">{{ about.backend.django_version }}</dd>
          <dt class="text-gray-500 dark:text-gray-400">DRF</dt>
          <dd class="text-gray-900 dark:text-gray-100 font-mono">{{ about.backend.drf_version }}</dd>
        </dl>
      </div>

      <!-- 环境信息 -->
      <div v-if="about" class="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 p-6 space-y-4">
        <h2 class="text-base font-semibold text-gray-900 dark:text-gray-100">环境</h2>
        <dl class="grid grid-cols-[auto_1fr] gap-x-6 gap-y-2 text-sm">
          <dt class="text-gray-500 dark:text-gray-400">调试模式</dt>
          <dd>
            <UBadge :color="about.environment.debug ? 'warning' : 'success'" variant="subtle" size="xs">
              {{ about.environment.debug ? '开启' : '关闭' }}
            </UBadge>
          </dd>
          <dt class="text-gray-500 dark:text-gray-400">数据库</dt>
          <dd class="text-gray-900 dark:text-gray-100 font-mono">{{ about.environment.database }}</dd>
        </dl>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ layout: 'default' })

const { api } = useApi()
const runtimeConfig = useRuntimeConfig().public

interface AboutInfo {
  backend: {
    version: string
    git_hash: string | null
    build_date: string | null
    python_version: string
    django_version: string
    drf_version: string
  }
  environment: {
    debug: boolean
    database: string
  }
}

const about = ref<AboutInfo | null>(null)
const loading = ref(true)
const error = ref('')

onMounted(async () => {
  try {
    about.value = await api<AboutInfo>('/api/about/')
  } catch (e: any) {
    error.value = '无法获取系统信息'
  } finally {
    loading.value = false
  }
})
</script>
