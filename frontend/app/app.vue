<template>
  <UApp>
    <NuxtLayout>
      <NuxtPage />
    </NuxtLayout>
  </UApp>
</template>

<script setup lang="ts">
const colorMode = useColorMode()
const { settings } = useUserSettings()

useHead({
  htmlAttrs: { lang: 'zh-CN' },
  bodyAttrs: { class: 'font-sans antialiased' },
})

watch(() => settings.value.theme, (theme) => {
  colorMode.preference = theme === 'auto' ? 'system' : theme
}, { immediate: true })
</script>
