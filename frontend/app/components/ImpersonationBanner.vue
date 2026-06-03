<template>
  <div
    v-if="user?.impersonated_by"
    class="flex items-center justify-center gap-3 px-4 py-2 bg-amber-500 text-white text-sm font-medium"
    role="alert"
  >
    <UIcon name="i-heroicons-exclamation-triangle" class="w-4 h-4" />
    <span>您正在以「{{ user.name || user.username }}」的身份操作</span>
    <UButton size="xs" color="neutral" variant="solid" :loading="returning" @click="onReturn">
      返回管理员
    </UButton>
  </div>
</template>

<script setup lang="ts">
const { user, stopImpersonation } = useAuth()
const returning = ref(false)

async function onReturn() {
  returning.value = true
  try {
    await stopImpersonation()
  } finally {
    returning.value = false
  }
}
</script>
