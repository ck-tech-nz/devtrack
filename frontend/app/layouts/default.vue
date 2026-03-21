<template>
  <div class="flex h-screen bg-gray-50/50 dark:bg-gray-950">
    <AppSidebar />
    <div class="flex-1 flex flex-col min-w-0 overflow-hidden">
      <AppHeader />
      <main class="flex-1 overflow-y-auto p-6 lg:p-8">
        <slot />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
onErrorCaptured((err) => {
  console.error('[PAGE ERROR]', err)
  return false
})
</script>
