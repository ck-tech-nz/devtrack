<template>
  <div v-if="issue" class="space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <div class="flex items-center space-x-3">
          <h1 class="text-2xl font-semibold text-gray-900">{{ issue.id }}</h1>
          <UBadge :color="priorityColor(issue.priority)" variant="subtle">{{ issue.priority }}</UBadge>
          <UBadge :color="statusColor(issue.status)" variant="subtle">{{ issue.status }}</UBadge>
        </div>
        <p class="text-lg text-gray-700 mt-1">{{ issue.title }}</p>
      </div>
    </div>
    <div class="flex items-center space-x-3">
      <UButton v-if="!issue.branch_name" color="primary" size="sm" icon="i-heroicons-code-bracket" @click="createBranch">创建分支</UButton>
      <div v-else class="flex items-center bg-crystal-50 text-crystal-700 rounded-lg px-3 py-1.5 text-sm">
        <UIcon name="i-heroicons-code-bracket" class="w-4 h-4 mr-2" />
        {{ issue.branch_name }}
      </div>
      <UButton v-for="action in statusActions" :key="action.label" variant="outline" color="neutral" size="sm" @click="action.handler">{{ action.label }}</UButton>
    </div>
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <div class="lg:col-span-2 space-y-6">
        <div class="bg-white rounded-xl border border-gray-100 p-5">
          <h3 class="text-sm font-semibold text-gray-900 mb-3">问题描述</h3>
          <p class="text-sm text-gray-600 leading-relaxed">{{ issue.description }}</p>
        </div>
        <div class="bg-white rounded-xl border border-gray-100 p-5">
          <div class="flex items-center justify-between mb-3">
            <h3 class="text-sm font-semibold text-gray-900">AI 分析</h3>
            <ServiceStatusDot :online="isOnline('ai')" />
          </div>
          <template v-if="isOnline('ai') && issue.ai_analysis">
            <div class="space-y-3">
              <div>
                <span class="text-xs text-gray-400">建议优先级</span>
                <UBadge :color="priorityColor(issue.ai_analysis.suggested_priority)" variant="subtle" size="xs" class="ml-2">{{ issue.ai_analysis.suggested_priority }}</UBadge>
              </div>
              <div>
                <span class="text-xs text-gray-400">建议标签</span>
                <div class="flex gap-1 mt-1">
                  <UBadge v-for="l in issue.ai_analysis.suggested_labels" :key="l" color="primary" variant="subtle" size="xs">{{ l }}</UBadge>
                </div>
              </div>
              <div>
                <span class="text-xs text-gray-400">解决建议</span>
                <ul class="mt-1 space-y-1">
                  <li v-for="h in issue.ai_analysis.resolution_hints" :key="h" class="text-sm text-gray-600 flex items-start">
                    <UIcon name="i-heroicons-light-bulb" class="w-4 h-4 text-amber-400 mr-1.5 mt-0.5 flex-shrink-0" />
                    {{ h }}
                  </li>
                </ul>
              </div>
              <div>
                <span class="text-xs text-gray-400">关联代码文件</span>
                <div class="mt-1 space-y-1">
                  <div v-for="f in issue.ai_analysis.related_files" :key="f" class="text-sm text-crystal-600 font-mono">{{ f }}</div>
                </div>
              </div>
            </div>
          </template>
          <div v-else-if="!isOnline('ai')" class="text-sm text-gray-400 flex items-center">
            <UIcon name="i-heroicons-exclamation-circle" class="w-4 h-4 mr-2" />AI 服务暂不可用
          </div>
          <div v-else class="text-sm text-gray-400">暂无 AI 分析结果</div>
        </div>
        <div class="bg-white rounded-xl border border-gray-100 p-5">
          <div class="flex items-center justify-between mb-3">
            <h3 class="text-sm font-semibold text-gray-900">GitHub 关联</h3>
            <ServiceStatusDot :online="isOnline('github')" />
          </div>
          <template v-if="isOnline('github')">
            <div v-if="issue.linked_commits.length || issue.linked_prs.length" class="space-y-3">
              <div v-if="issue.linked_prs.length">
                <span class="text-xs text-gray-400">关联 PR</span>
                <div class="mt-1 space-y-1">
                  <div v-for="pr in issue.linked_prs" :key="pr" class="text-sm text-crystal-600 flex items-center">
                    <UIcon name="i-heroicons-arrow-up-tray" class="w-4 h-4 mr-1.5" />PR #{{ pr }}
                  </div>
                </div>
              </div>
              <div v-if="issue.linked_commits.length">
                <span class="text-xs text-gray-400">关联 Commit</span>
                <div class="mt-1 space-y-1">
                  <div v-for="sha in issue.linked_commits" :key="sha" class="text-sm text-gray-600 font-mono">{{ sha }}</div>
                </div>
              </div>
            </div>
            <div v-else class="text-sm text-gray-400">暂无关联的 GitHub 记录</div>
          </template>
          <div v-else class="text-sm text-gray-400 flex items-center">
            <UIcon name="i-heroicons-exclamation-circle" class="w-4 h-4 mr-2" />GitHub 连接不可用
          </div>
        </div>
        <div v-if="issue.cause || issue.solution" class="bg-white rounded-xl border border-gray-100 p-5">
          <h3 class="text-sm font-semibold text-gray-900 mb-3">分析记录</h3>
          <div class="space-y-3">
            <div v-if="issue.cause"><span class="text-xs text-gray-400">原因分析</span><p class="text-sm text-gray-600 mt-1">{{ issue.cause }}</p></div>
            <div v-if="issue.solution"><span class="text-xs text-gray-400">解决办法</span><p class="text-sm text-gray-600 mt-1">{{ issue.solution }}</p></div>
          </div>
        </div>
      </div>
      <div class="space-y-4">
        <div class="bg-white rounded-xl border border-gray-100 p-5 space-y-4">
          <div><span class="text-xs text-gray-400">负责人</span><p class="text-sm text-gray-900 mt-0.5">{{ getUserName(issue.assignee) }}</p></div>
          <div><span class="text-xs text-gray-400">提出人</span><p class="text-sm text-gray-900 mt-0.5">{{ getUserName(issue.reporter) }}</p></div>
          <div><span class="text-xs text-gray-400">标签</span><div class="flex flex-wrap gap-1 mt-1"><UBadge v-for="l in issue.labels" :key="l" color="neutral" variant="subtle" size="xs">{{ l }}</UBadge></div></div>
          <div><span class="text-xs text-gray-400">创建时间</span><p class="text-sm text-gray-900 mt-0.5">{{ issue.created_at.slice(0, 10) }}</p></div>
          <div v-if="issue.resolved_at"><span class="text-xs text-gray-400">解决时间</span><p class="text-sm text-gray-900 mt-0.5">{{ issue.resolved_at.slice(0, 10) }}</p></div>
          <div v-if="issue.resolution_hours"><span class="text-xs text-gray-400">解决耗时</span><p class="text-sm text-gray-900 mt-0.5">{{ issue.resolution_hours }} 小时</p></div>
          <div v-if="issue.branch_merged_at"><span class="text-xs text-gray-400">分支合并时间</span><p class="text-sm text-gray-900 mt-0.5">{{ issue.branch_merged_at.slice(0, 10) }}</p></div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ layout: 'default' })
import { issues, getUserName } from '~/data/mock'

const route = useRoute()
const { isOnline } = useServiceStatus()

const issue = computed(() => issues.find(i => i.id === route.params.id))

function priorityColor(p: string) {
  return p === 'P0' ? 'error' : p === 'P1' ? 'warning' : p === 'P2' ? 'warning' : 'neutral'
}
function statusColor(s: string) {
  return s === '待处理' ? 'warning' : s === '进行中' ? 'info' : s === '已解决' ? 'success' : 'neutral'
}

function createBranch() {
  if (!issue.value) return
  const slug = issue.value.title.slice(0, 15).replace(/\s+/g, '-')
  const num = issue.value.id.replace('ISS-', '')
  issue.value.branch_name = `fix/iss-${num}-${slug}`
  issue.value.branch_created_at = new Date().toISOString()
}

const statusActions = computed(() => {
  if (!issue.value) return []
  const s = issue.value.status
  const actions = []
  if (s === '待处理') actions.push({ label: '开始处理', handler: () => { issue.value!.status = '进行中' } })
  if (s === '进行中') actions.push({ label: '标记已解决', handler: () => { issue.value!.status = '已解决'; issue.value!.resolved_at = new Date().toISOString() } })
  if (s === '已解决') actions.push({ label: '关闭', handler: () => { issue.value!.status = '已关闭' } })
  return actions
})
</script>
