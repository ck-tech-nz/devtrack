<template>
  <div class="space-y-6 max-w-4xl">
    <h1 class="text-2xl font-semibold text-gray-900 dark:text-gray-100">接口文档</h1>

    <div v-if="loading" class="flex items-center justify-center py-20">
      <div class="text-sm text-gray-400 dark:text-gray-500">加载中...</div>
    </div>

    <div v-else-if="error" class="text-sm text-red-500 py-10 text-center">{{ error }}</div>

    <template v-else-if="docs">
      <!-- 认证说明 -->
      <div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 p-6">
        <h2 class="text-base font-semibold text-gray-900 dark:text-gray-100 mb-4">认证方式</h2>
        <dl class="grid grid-cols-[auto_1fr] gap-x-6 gap-y-2 text-sm">
          <dt class="text-gray-500 dark:text-gray-400">类型</dt>
          <dd class="text-gray-900 dark:text-gray-100 font-mono">{{ docs.authentication.type }}</dd>
          <dt class="text-gray-500 dark:text-gray-400">请求头</dt>
          <dd class="text-gray-900 dark:text-gray-100 font-mono text-xs bg-gray-100 dark:bg-gray-800 px-2 py-1 rounded">{{ docs.authentication.header }}</dd>
          <dt class="text-gray-500 dark:text-gray-400">说明</dt>
          <dd class="text-gray-900 dark:text-gray-100">{{ docs.authentication.description }}</dd>
        </dl>
      </div>

      <!-- API Key 验证 -->
      <div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 p-6">
        <h2 class="text-base font-semibold text-gray-900 dark:text-gray-100 mb-4">API Key 验证</h2>
        <p class="text-sm text-gray-500 dark:text-gray-400 mb-4">输入 API Key 验证是否有效，查看绑定的项目和负责人。</p>
        <div class="flex gap-3">
          <UInput
            v-model="testApiKey"
            placeholder="输入 API Key"
            class="flex-1 font-mono"
            size="sm"
          />
          <UButton size="sm" :loading="testing" @click="testKey">验证</UButton>
        </div>
        <div v-if="testResult" class="mt-3 p-3 rounded-lg text-sm" :class="testResult.valid ? 'bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800' : 'bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800'">
          <div v-if="testResult.valid" class="space-y-1">
            <div class="text-green-700 dark:text-green-300 font-medium">API Key 有效</div>
            <dl class="grid grid-cols-[auto_1fr] gap-x-6 gap-y-2 text-sm text-green-800 dark:text-green-200">
              <dt>Key 名称</dt>
              <dd>{{ testResult.key_name }}</dd>
              <dt>绑定项目</dt>
              <dd>{{ testResult.project }}</dd>
              <dt>默认负责人</dt>
              <dd>{{ testResult.default_assignee || '未设置' }}</dd>
            </dl>
          </div>
          <div v-else class="text-red-700 dark:text-red-300">
            {{ testResult.detail || 'API Key 无效' }}
          </div>
        </div>
      </div>

      <!-- 接口列表 -->
      <div v-for="(endpoint, idx) in docs.endpoints" :key="idx" class="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 p-6">
        <div class="flex items-center gap-3 mb-4">
          <UBadge :color="endpoint.method === 'POST' ? 'success' : 'info'" variant="solid" size="sm" class="font-mono">
            {{ endpoint.method }}
          </UBadge>
          <code class="text-sm text-gray-700 dark:text-gray-300">{{ endpoint.path }}</code>
        </div>
        <h3 class="text-base font-semibold text-gray-900 dark:text-gray-100">{{ endpoint.summary }}</h3>
        <p class="text-sm text-gray-500 dark:text-gray-400 mt-1">{{ endpoint.description }}</p>

        <!-- 路径参数 -->
        <template v-if="endpoint.path_params?.length">
          <h4 class="text-sm font-semibold text-gray-700 dark:text-gray-300 mt-5 mb-2">路径参数</h4>
          <div class="w-full text-sm border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
            <table class="w-full">
              <thead class="bg-gray-50 dark:bg-gray-800">
                <tr>
                  <th class="text-left px-3 py-2 text-gray-600 dark:text-gray-400 font-medium text-xs">参数</th>
                  <th class="text-left px-3 py-2 text-gray-600 dark:text-gray-400 font-medium text-xs">类型</th>
                  <th class="text-left px-3 py-2 text-gray-600 dark:text-gray-400 font-medium text-xs">说明</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="p in endpoint.path_params" :key="p.name">
                  <td class="px-3 py-2 text-gray-800 dark:text-gray-200 border-t border-gray-100 dark:border-gray-800 font-mono">{{ p.name }}</td>
                  <td class="px-3 py-2 text-gray-800 dark:text-gray-200 border-t border-gray-100 dark:border-gray-800">{{ p.type }}</td>
                  <td class="px-3 py-2 text-gray-800 dark:text-gray-200 border-t border-gray-100 dark:border-gray-800">{{ p.description }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </template>

        <!-- 查询参数 -->
        <template v-if="endpoint.query_params?.length">
          <h4 class="text-sm font-semibold text-gray-700 dark:text-gray-300 mt-5 mb-2">查询参数</h4>
          <div class="w-full text-sm border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
            <table class="w-full">
              <thead class="bg-gray-50 dark:bg-gray-800">
                <tr>
                  <th class="text-left px-3 py-2 text-gray-600 dark:text-gray-400 font-medium text-xs">参数</th>
                  <th class="text-left px-3 py-2 text-gray-600 dark:text-gray-400 font-medium text-xs">类型</th>
                  <th class="text-left px-3 py-2 text-gray-600 dark:text-gray-400 font-medium text-xs">说明</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="p in endpoint.query_params" :key="p.name">
                  <td class="px-3 py-2 text-gray-800 dark:text-gray-200 border-t border-gray-100 dark:border-gray-800 font-mono">{{ p.name }}</td>
                  <td class="px-3 py-2 text-gray-800 dark:text-gray-200 border-t border-gray-100 dark:border-gray-800">{{ p.type }}</td>
                  <td class="px-3 py-2 text-gray-800 dark:text-gray-200 border-t border-gray-100 dark:border-gray-800">{{ p.description }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </template>

        <!-- 请求体 -->
        <template v-if="endpoint.request_body">
          <h4 class="text-sm font-semibold text-gray-700 dark:text-gray-300 mt-5 mb-2">请求体</h4>
          <div class="w-full text-sm border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
            <table class="w-full">
              <thead class="bg-gray-50 dark:bg-gray-800">
                <tr>
                  <th class="text-left px-3 py-2 text-gray-600 dark:text-gray-400 font-medium text-xs">字段</th>
                  <th class="text-left px-3 py-2 text-gray-600 dark:text-gray-400 font-medium text-xs">类型</th>
                  <th class="text-left px-3 py-2 text-gray-600 dark:text-gray-400 font-medium text-xs">必填</th>
                  <th class="text-left px-3 py-2 text-gray-600 dark:text-gray-400 font-medium text-xs">说明</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="f in endpoint.request_body.fields" :key="f.name">
                  <td class="px-3 py-2 text-gray-800 dark:text-gray-200 border-t border-gray-100 dark:border-gray-800 font-mono">{{ f.name }}</td>
                  <td class="px-3 py-2 text-gray-800 dark:text-gray-200 border-t border-gray-100 dark:border-gray-800">{{ f.type }}</td>
                  <td class="px-3 py-2 text-gray-800 dark:text-gray-200 border-t border-gray-100 dark:border-gray-800">
                    <UBadge v-if="f.required" color="error" variant="subtle" size="xs">必填</UBadge>
                    <span v-else class="text-gray-400">可选</span>
                  </td>
                  <td class="px-3 py-2 text-gray-800 dark:text-gray-200 border-t border-gray-100 dark:border-gray-800">{{ f.description }}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <h4 class="text-sm font-semibold text-gray-700 dark:text-gray-300 mt-5 mb-2">请求示例</h4>
          <pre class="text-xs bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4 overflow-x-auto text-gray-800 dark:text-gray-200">{{ JSON.stringify(endpoint.request_body.example, null, 2) }}</pre>
        </template>

        <!-- 响应 -->
        <h4 class="text-sm font-semibold text-gray-700 dark:text-gray-300 mt-5 mb-2">响应</h4>
        <div v-for="r in endpoint.responses" :key="r.status" class="mb-3">
          <div class="flex items-center gap-2 mb-1">
            <UBadge :color="r.status < 300 ? 'success' : r.status < 500 ? 'warning' : 'error'" variant="subtle" size="xs">
              {{ r.status }}
            </UBadge>
            <span class="text-sm text-gray-600 dark:text-gray-400">{{ r.description }}</span>
          </div>
          <pre v-if="r.example" class="text-xs bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4 overflow-x-auto text-gray-800 dark:text-gray-200">{{ JSON.stringify(r.example, null, 2) }}</pre>
        </div>
      </div>

      <!-- 错误格式 -->
      <div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 p-6">
        <h2 class="text-base font-semibold text-gray-900 dark:text-gray-100 mb-4">错误格式</h2>
        <p class="text-sm text-gray-500 dark:text-gray-400 mb-3">{{ docs.error_format.description }}</p>
        <pre class="text-xs bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4 overflow-x-auto text-gray-800 dark:text-gray-200">{{ JSON.stringify(docs.error_format.example, null, 2) }}</pre>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ layout: 'default' })

const { api } = useApi()

const docs = ref<any>(null)
const loading = ref(true)
const error = ref('')

const testApiKey = ref('')
const testing = ref(false)
const testResult = ref<any>(null)

onMounted(async () => {
  try {
    docs.value = await api<any>('/api/external/docs/')
  } catch (e: any) {
    error.value = '无法获取接口文档'
  } finally {
    loading.value = false
  }
})

async function testKey() {
  if (!testApiKey.value.trim()) return
  testing.value = true
  testResult.value = null
  try {
    const resp = await $fetch<any>('/api/external/test-key/', {
      method: 'POST',
      headers: { Authorization: `Bearer ${testApiKey.value.trim()}` },
    })
    testResult.value = resp
  } catch (e: any) {
    testResult.value = { valid: false, detail: 'API Key 无效或未提供' }
  } finally {
    testing.value = false
  }
}
</script>
