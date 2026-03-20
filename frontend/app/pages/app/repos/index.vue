<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <h1 class="text-2xl font-semibold text-gray-900">GitHub 仓库</h1>
      <ServiceStatusDot :online="isOnline('github')" />
    </div>
    <template v-if="isOnline('github')">
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <NuxtLink v-for="repo in repos" :key="repo.id" :to="`/app/repos/${repo.id}`" class="bg-white rounded-xl border border-gray-100 p-5 hover:shadow-sm transition-shadow block">
          <div class="flex items-center justify-between mb-2">
            <h3 class="font-semibold text-gray-900">{{ repo.full_name }}</h3>
            <UBadge :color="repo.status === '在线' ? 'success' : 'neutral'" variant="subtle" size="xs">{{ repo.status }}</UBadge>
          </div>
          <p class="text-sm text-gray-500 mb-3">{{ repo.description }}</p>
          <div class="flex items-center text-xs text-gray-400 space-x-4">
            <span class="flex items-center"><UIcon name="i-heroicons-code-bracket" class="w-3.5 h-3.5 mr-1" />{{ repo.language }}</span>
            <span class="flex items-center"><UIcon name="i-heroicons-star" class="w-3.5 h-3.5 mr-1" />{{ repo.stars }}</span>
            <span>绑定于 {{ repo.connected_at.slice(0, 10) }}</span>
          </div>
        </NuxtLink>
      </div>
    </template>
    <div v-else class="bg-white rounded-xl border border-gray-100 p-12 text-center">
      <UIcon name="i-heroicons-exclamation-circle" class="w-12 h-12 text-gray-300 mx-auto mb-3" />
      <p class="text-gray-500">GitHub 连接不可用</p>
      <p class="text-sm text-gray-400 mt-1">请检查 GitHub API 连接配置</p>
    </div>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ layout: 'default' })
import { repos } from '~/data/mock'
const { isOnline } = useServiceStatus()
</script>
