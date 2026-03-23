<template>
  <div class="w-full max-w-sm">
    <div class="text-center mb-8">
      <img src="~/assets/images/logo-icon.svg" alt="DevTrakr" class="w-14 h-14 mx-auto mb-4" />
      <h1 class="text-2xl font-semibold text-gray-900">DevTrakr</h1>
      <p class="text-sm text-gray-400 mt-1">项目管理平台</p>
    </div>

    <form class="bg-white rounded-2xl shadow-xl shadow-gray-200/50 border border-gray-100 p-8" @submit.prevent="handleRegister">
      <h2 class="text-lg font-semibold text-gray-900 mb-6">注册</h2>
      <div class="space-y-4">
        <UFormField label="用户名" required>
          <UInput v-model="form.username" placeholder="请输入用户名" icon="i-heroicons-user" size="lg" class="w-full" />
        </UFormField>
        <UFormField label="密码" required>
          <UInput v-model="form.password" type="password" placeholder="请输入密码" icon="i-heroicons-lock-closed" size="lg" class="w-full" />
        </UFormField>
        <UFormField label="确认密码" required>
          <UInput v-model="form.password_confirm" type="password" placeholder="请再次输入密码" icon="i-heroicons-lock-closed" size="lg" class="w-full" />
        </UFormField>
        <UFormField label="昵称">
          <UInput v-model="form.name" placeholder="请输入昵称" icon="i-heroicons-user-circle" size="lg" class="w-full" />
        </UFormField>
        <UFormField label="邮箱" hint="用于接收通知">
          <UInput v-model="form.email" type="email" placeholder="请输入邮箱" icon="i-heroicons-envelope" size="lg" class="w-full" />
        </UFormField>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">选择头像</label>
          <AvatarPicker v-model="form.avatar" />
        </div>
        <p v-if="error" class="text-sm text-red-500">{{ error }}</p>
        <UButton block size="lg" color="primary" :loading="loading" type="submit">注册</UButton>
      </div>
    </form>

    <p class="text-center text-sm text-gray-500 mt-4">
      已有账号？
      <NuxtLink to="/" class="text-crystal-500 hover:text-crystal-700 font-medium">返回登录</NuxtLink>
    </p>
    <p class="text-center text-xs text-gray-400 mt-6">&copy; 2026 DevTrakr 项目管理平台</p>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ layout: 'auth' })

const { randomAvatarId } = useAvatars()

const form = ref({
  username: '',
  password: '',
  password_confirm: '',
  name: '',
  email: '',
  avatar: randomAvatarId(),
})
const error = ref('')
const loading = ref(false)

async function handleRegister() {
  error.value = ''
  if (form.value.password !== form.value.password_confirm) {
    error.value = '两次密码输入不一致'
    return
  }
  loading.value = true
  try {
    await $fetch('/api/auth/register/', {
      method: 'POST',
      body: form.value,
    })
    await navigateTo('/?registered=1')
  } catch (e: any) {
    const data = e?.data || e?.response?._data
    if (data && typeof data === 'object') {
      const msgs = Object.entries(data)
        .map(([k, v]) => Array.isArray(v) ? v.join(', ') : v)
        .join('; ')
      error.value = msgs || '注册失败，请重试'
    } else {
      error.value = '注册失败，请重试'
    }
  } finally {
    loading.value = false
  }
}
</script>
