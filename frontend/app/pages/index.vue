<template>
  <div class="w-full max-w-sm">
    <div class="text-center mb-8">
      <div class="w-14 h-14 rounded-2xl bg-crystal-500 flex items-center justify-center mx-auto mb-4 shadow-lg shadow-crystal-200">
        <span class="text-white font-bold text-2xl">D</span>
      </div>
      <h1 class="text-2xl font-semibold text-gray-900">DevTrack</h1>
      <p class="text-sm text-gray-400 mt-1">项目管理平台</p>
    </div>

    <div class="bg-white rounded-2xl shadow-xl shadow-gray-200/50 border border-gray-100 p-8">
      <h2 class="text-lg font-semibold text-gray-900 mb-6">登录</h2>
      <div class="space-y-4">
        <UFormField label="用户名">
          <UInput v-model="username" placeholder="请输入用户名" icon="i-heroicons-user" size="lg" />
        </UFormField>
        <UFormField label="密码">
          <UInput v-model="password" type="password" placeholder="请输入密码" icon="i-heroicons-lock-closed" size="lg" />
        </UFormField>
        <p v-if="error" class="text-sm text-red-500">{{ error }}</p>
        <UButton block size="lg" color="primary" :loading="loading" @click="handleLogin">登录</UButton>
      </div>
    </div>

    <p class="text-center text-xs text-gray-400 mt-6">&copy; 2026 DevTrack 项目管理平台</p>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ layout: 'auth' })

const username = ref('admin')
const password = ref('')
const error = ref('')
const loading = ref(false)

const { setTokens } = useApi()
const { fetchMe } = useAuth()

async function handleLogin() {
  error.value = ''
  loading.value = true
  try {
    const data = await $fetch<{ access: string; refresh: string }>('/api/auth/login/', {
      method: 'POST',
      body: { username: username.value, password: password.value },
    })
    setTokens(data.access, data.refresh)
    await fetchMe()
    await navigateTo('/app/dashboard')
  } catch (e: any) {
    error.value = '用户名或密码错误'
  } finally {
    loading.value = false
  }
}
</script>
