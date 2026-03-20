<template>
  <NuxtLayout>
    <NuxtPage />
  </NuxtLayout>
</template>

<script setup lang="ts">
useHead({
  htmlAttrs: { lang: 'zh-CN' },
  bodyAttrs: { class: 'font-sans antialiased' },
})
</script>

<style>
body {
  font-family: 'Inter', ui-sans-serif, system-ui, -apple-system, sans-serif;
}
</style>
