<template>
  <UApp>
    <NuxtLayout>
      <NuxtPage />
    </NuxtLayout>
  </UApp>
</template>

<script setup lang="ts">
useHead({
  htmlAttrs: { lang: 'zh-CN' },
  bodyAttrs: { class: 'font-sans antialiased' },
})
</script>
