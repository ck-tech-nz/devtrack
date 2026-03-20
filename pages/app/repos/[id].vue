<template>
  <div v-if="!isOnline('github')" class="space-y-6">
    <h1 class="text-2xl font-semibold text-gray-900">GitHub 仓库</h1>
    <div class="bg-white rounded-xl border border-gray-100 p-12 text-center">
      <UIcon name="i-heroicons-exclamation-circle" class="w-12 h-12 text-gray-300 mx-auto mb-3" />
      <p class="text-gray-500">GitHub 连接不可用</p>
      <p class="text-sm text-gray-400 mt-1">请检查 GitHub API 连接配置</p>
    </div>
  </div>
  <div v-else-if="repo" class="space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-semibold text-gray-900">{{ repo.full_name }}</h1>
        <p class="text-sm text-gray-500 mt-1">{{ repo.description }}</p>
      </div>
      <div class="flex items-center space-x-3">
        <UBadge color="gray" variant="subtle">{{ repo.language }}</UBadge>
        <UBadge color="gray" variant="subtle"><UIcon name="i-heroicons-star" class="w-3 h-3 mr-1" />{{ repo.stars }}</UBadge>
      </div>
    </div>
    <div class="bg-white rounded-xl border border-gray-100 p-5">
      <h3 class="text-sm font-semibold text-gray-900 mb-3">最近提交</h3>
      <div class="divide-y divide-gray-50">
        <div v-for="commit in repo.recent_commits" :key="commit.sha" class="py-3 first:pt-0 last:pb-0">
          <div class="flex items-center justify-between">
            <p class="text-sm text-gray-900">{{ commit.message }}</p>
            <span class="text-xs text-gray-400 font-mono ml-4 flex-shrink-0">{{ commit.sha }}</span>
          </div>
          <div class="flex items-center mt-1 text-xs text-gray-400 space-x-3">
            <span>{{ commit.author }}</span>
            <span>{{ commit.date.slice(0, 10) }}</span>
          </div>
        </div>
      </div>
    </div>
    <div class="bg-white rounded-xl border border-gray-100 p-5">
      <h3 class="text-sm font-semibold text-gray-900 mb-3">Open Pull Requests ({{ repo.open_prs.length }})</h3>
      <div v-if="repo.open_prs.length" class="divide-y divide-gray-50">
        <div v-for="pr in repo.open_prs" :key="pr.number" class="py-3 first:pt-0 last:pb-0 flex items-center justify-between">
          <div><span class="text-sm text-crystal-600 font-medium">#{{ pr.number }}</span><span class="text-sm text-gray-900 ml-2">{{ pr.title }}</span></div>
          <div class="text-xs text-gray-400">{{ pr.author }} &middot; {{ pr.created_at.slice(0, 10) }}</div>
        </div>
      </div>
      <p v-else class="text-sm text-gray-400">暂无 Open PR</p>
    </div>
    <div class="bg-white rounded-xl border border-gray-100 p-5">
      <h3 class="text-sm font-semibold text-gray-900 mb-3">Open Issues ({{ repo.open_issues.length }})</h3>
      <div v-if="repo.open_issues.length" class="divide-y divide-gray-50">
        <div v-for="issue in repo.open_issues" :key="issue.number" class="py-3 first:pt-0 last:pb-0 flex items-center justify-between">
          <div><span class="text-sm text-crystal-600 font-medium">#{{ issue.number }}</span><span class="text-sm text-gray-900 ml-2">{{ issue.title }}</span></div>
          <div class="flex items-center space-x-2"><UBadge v-for="l in issue.labels" :key="l" color="gray" variant="subtle" size="xs">{{ l }}</UBadge></div>
        </div>
      </div>
      <p v-else class="text-sm text-gray-400">暂无 Open Issue</p>
    </div>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ layout: 'default' })
import { repos } from '~/data/mock'
const route = useRoute()
const { isOnline } = useServiceStatus()
const repo = computed(() => repos.find(r => r.id === route.params.id))
</script>
