<template>
  <div v-if="loading" class="flex items-center justify-center py-20">
    <div class="text-sm text-gray-400 dark:text-gray-500">加载中...</div>
  </div>

  <div v-else-if="issue" class="space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div class="flex items-center space-x-3">
        <NuxtLink to="/app/issues" class="text-gray-400 dark:text-gray-500 hover:text-gray-600">
          <UIcon name="i-heroicons-arrow-left" class="w-5 h-5" />
        </NuxtLink>
        <h1 class="text-2xl font-semibold">
          <span class="text-gray-900 dark:text-gray-100">{{ issue.title }}</span>
          <span class="text-gray-400 dark:text-gray-500 font-normal ml-2">#{{ issue.id }}</span>
        </h1>
      </div>
      <div class="flex items-center space-x-2"></div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <!-- Main content -->
      <div class="lg:col-span-2 space-y-4">
        <div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 p-5">
          <div class="space-y-4">
            <!-- 标题 -->
            <div class="form-row">
              <div class="flex items-center justify-between">
                <label>标题</label>
                <UButton v-if="isFieldDirty('title')" size="xs" variant="soft" :loading="savingField === 'title'" @click="saveField('title')">保存</UButton>
              </div>
              <UInput v-model="form.title" />
            </div>

            <!-- 描述 -->
            <div class="form-row">
              <div class="flex items-center justify-between">
                <label>描述</label>
                <UButton v-if="isFieldDirty('description')" size="xs" variant="soft" :loading="savingField === 'description'" @click="saveField('description')">保存</UButton>
              </div>
              <MarkdownEditor ref="descriptionEditor" v-model="form.description" placeholder="添加描述..." :default-mode="isNewIssue ? 'edit' : 'preview'" @upload-complete="handleUploadComplete" />
            </div>

            <!-- 优先级 & 状态 -->
            <div class="form-grid-2">
              <div class="form-row">
                <label>优先级</label>
                <div class="flex items-center gap-2 flex-wrap">
                  <button
                    v-for="p in priorityItems"
                    :key="p.value"
                    class="px-3 py-1 rounded-full text-xs font-medium transition-colors"
                    :class="issue.priority === p.value ? p.activeClass : 'bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700'"
                    @click="updateField('priority', p.value)"
                  >{{ p.label }}</button>
                </div>
              </div>
              <div class="form-row">
                <label>状态</label>
                <div class="flex items-center gap-2 flex-wrap">
                  <button
                    v-for="s in statusItems"
                    :key="s.value"
                    class="px-3 py-1 rounded-full text-xs font-medium transition-colors"
                    :class="issue.status === s.value ? s.activeClass : 'bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700'"
                    @click="handleStatusClick(s.value)"
                  >{{ s.label }}</button>
                </div>
              </div>
            </div>

            <div class="form-grid-2">
              <div class="form-row">
                <label>负责人</label>
                <USelect v-model="form.assignee" :items="assigneeItems" placeholder="选择负责人" value-key="value" @update:model-value="(v: string) => autoSave('assignee', v)" />
              </div>
              <div class="form-row">
                <label>求助</label>
                <USelectMenu v-model="form.helpers" :items="helperItems" multiple placeholder="选择协助人" value-key="value" label-key="label" @update:model-value="(v: string[]) => autoSave('helpers', v)" />
              </div>
            </div>
            <div v-if="labelItems.length" class="form-row">
              <label>标签</label>
              <div class="flex items-center gap-2 flex-wrap">
                <button
                  v-for="lbl in labelItems"
                  :key="lbl"
                  class="px-3 py-1 rounded-full text-xs font-medium transition-colors"
                  :class="form.labels.includes(lbl) ? 'bg-primary-100 text-primary-700 dark:bg-primary-900 dark:text-primary-300' : 'bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700'"
                  @click="toggleLabel(lbl)"
                >{{ lbl }}</button>
              </div>
            </div>
          </div>
        </div>

        <div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 p-5">
          <h3 class="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-4">分析记录</h3>
          <div class="space-y-4">
            <div class="form-row">
              <div class="flex items-center justify-between">
                <label>备注</label>
                <UButton v-if="isFieldDirty('remark')" size="xs" variant="soft" :loading="savingField === 'remark'" @click="saveField('remark')">保存</UButton>
              </div>
              <UTextarea v-model="form.remark" :rows="2" placeholder="备注信息" />
            </div>
            <div class="form-row">
              <div class="flex items-center justify-between">
                <label>原因分析</label>
                <UButton v-if="isFieldDirty('cause')" size="xs" variant="soft" :loading="savingField === 'cause'" @click="saveField('cause')">保存</UButton>
              </div>
              <UTextarea v-model="form.cause" :rows="3" placeholder="问题原因" />
            </div>
            <div class="form-row">
              <div class="flex items-center justify-between">
                <label>解决方案</label>
                <UButton v-if="isFieldDirty('solution')" size="xs" variant="soft" :loading="savingField === 'solution'" @click="saveField('solution')">保存</UButton>
              </div>
              <UTextarea v-model="form.solution" :rows="3" placeholder="解决办法" />
            </div>
          </div>
        </div>
      </div>

      <!-- Sidebar -->
      <div class="space-y-4">
        <div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 p-5 space-y-3">
          <div class="flex items-center justify-between">
            <h3 class="text-sm font-semibold text-gray-900 dark:text-gray-100">AI 分析</h3>
            <div class="flex items-center gap-2">
              <ServiceStatusDot :online="isOnline('ai')" />
              <UButton
                v-if="issue.repo"
                size="xs"
                variant="soft"
                icon="i-heroicons-cpu-chip"
                :loading="aiAnalyzing"
                :disabled="aiAnalyzing || issueRepo?.clone_status !== 'cloned'"
                @click="triggerAIAnalysis"
              >{{ aiAnalyzing ? '分析中...' : '分析' }}</UButton>
            </div>
          </div>

          <!-- 运行状态 -->
          <div v-if="aiAnalyzing" class="space-y-2">
            <div class="flex items-center gap-2">
              <UIcon name="i-heroicons-cpu-chip" class="w-4 h-4 text-blue-500 animate-spin" />
              <span class="text-sm text-blue-500 dark:text-blue-400">正在分析代码...</span>
            </div>
            <div class="text-xs text-gray-400">opencode 正在分析仓库代码，通常需要 1-3 分钟</div>
            <div class="w-full bg-gray-100 dark:bg-gray-800 rounded-full h-1.5 overflow-hidden">
              <div class="bg-blue-500 h-1.5 rounded-full ai-progress-bar"></div>
            </div>
          </div>

          <!-- 前置条件提示 -->
          <div v-else-if="!issue.repo" class="text-sm text-gray-400 dark:text-gray-500">请先关联仓库</div>
          <div v-else-if="issueRepo?.clone_status !== 'cloned'" class="text-sm text-gray-400 dark:text-gray-500">请先同步仓库代码</div>

          <!-- 分析历史 -->
          <div v-if="analyses.length" class="space-y-2 max-h-96 overflow-y-auto">
            <div v-for="a in analyses" :key="a.id" class="rounded-lg border text-sm"
              :class="a.status === 'failed' ? 'border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/20' : 'border-blue-200 dark:border-blue-800 bg-blue-50 dark:bg-blue-900/20'">
              <div class="px-3 py-2">
                <div class="flex items-center justify-between text-xs mb-1">
                  <div class="flex items-center gap-1" :class="a.status === 'failed' ? 'text-red-600 dark:text-red-400' : 'text-blue-600 dark:text-blue-400'">
                    <UIcon name="i-heroicons-cpu-chip" class="w-3 h-3" />
                    <span>{{ a.created_at?.slice(0, 16).replace('T', ' ') }}</span>
                  </div>
                  <UBadge :color="a.triggered_by === 'manual' ? 'primary' : 'neutral'" variant="subtle" size="xs">
                    {{ a.triggered_by === 'manual' ? '手动' : '自动' }}
                  </UBadge>
                </div>
                <div v-if="a.status === 'failed'" class="text-xs text-red-600 dark:text-red-400">{{ a.error_message }}</div>
                <div v-else-if="a.status === 'running'" class="text-xs text-blue-500">分析中...</div>
                <template v-else-if="a.results">
                  <div v-for="(content, field) in a.results" :key="field" class="mt-1">
                    <div class="text-xs font-medium text-gray-500 dark:text-gray-400">{{ fieldLabel(field as string) }}</div>
                    <div class="markdown-body text-sm mt-0.5 text-gray-700 dark:text-gray-300 max-h-60 overflow-y-auto" v-html="renderMarkdown(content as string)"></div>
                  </div>
                </template>
              </div>
            </div>
          </div>
          <p v-else-if="!aiAnalyzing && issue.repo && issueRepo?.clone_status === 'cloned'" class="text-sm text-gray-400 dark:text-gray-500">暂无分析记录</p>
        </div>

        <div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 p-5 space-y-3">
          <h3 class="text-sm font-semibold text-gray-900 dark:text-gray-100">信息</h3>
          <div class="grid grid-cols-2 gap-3">
            <div class="text-sm">
              <span class="text-gray-400 dark:text-gray-500">提出人</span>
              <p class="text-gray-900 dark:text-gray-100 mt-0.5">{{ issue.reporter_name || '-' }}</p>
            </div>
            <div class="text-sm">
              <span class="text-gray-400 dark:text-gray-500">创建时间</span>
              <p class="text-gray-900 dark:text-gray-100 mt-0.5">{{ issue.created_at?.slice(0, 10) }}</p>
            </div>
          </div>
          <div v-if="issue.resolved_at || issue.resolution_hours" class="grid grid-cols-2 gap-3">
            <div v-if="issue.resolved_at" class="text-sm">
              <span class="text-gray-400 dark:text-gray-500">解决时间</span>
              <p class="text-gray-900 dark:text-gray-100 mt-0.5">{{ issue.resolved_at.slice(0, 10) }}</p>
            </div>
            <div v-if="issue.resolution_hours" class="text-sm">
              <span class="text-gray-400 dark:text-gray-500">解决耗时</span>
              <p class="text-gray-900 dark:text-gray-100 mt-0.5">{{ issue.resolution_hours }}h</p>
            </div>
          </div>
          <div class="grid grid-cols-2 gap-3">
            <div class="form-row">
              <label class="text-gray-400 dark:text-gray-500">预计完成</label>
              <UInput v-model="form.estimated_completion" type="date" @update:model-value="(v: string) => autoSave('estimated_completion', v)" />
            </div>
            <div class="form-row">
              <div class="flex items-center justify-between">
                <label class="text-gray-400 dark:text-gray-500">实际工时</label>
                <UButton v-if="isFieldDirty('actual_hours')" size="xs" variant="soft" :loading="savingField === 'actual_hours'" @click="saveField('actual_hours')">保存</UButton>
              </div>
              <UInput v-model="form.actual_hours" type="number" placeholder="小时" />
            </div>
          </div>
        </div>

        <!-- 关联附件 -->
        <div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 p-5 space-y-3">
          <div class="flex items-center justify-between">
            <h3 class="text-sm font-semibold text-gray-900 dark:text-gray-100">关联附件</h3>
            <UButton size="xs" variant="soft" icon="i-heroicons-paper-clip" @click="attachmentInputRef?.click()">添加</UButton>
          </div>
          <input ref="attachmentInputRef" type="file" multiple class="hidden" @change="handleAttachmentSelect" />

          <!-- 图片附件：缩略图网格 -->
          <div v-if="imageAttachments.length" class="grid grid-cols-2 gap-2">
            <div
              v-for="att in imageAttachments"
              :key="att.id"
              class="relative group rounded-lg overflow-hidden border border-gray-100 dark:border-gray-800"
            >
              <img :src="att.file_url" :alt="att.file_name" class="w-full h-20 object-cover" :title="att.file_name" />
              <div class="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-end justify-between p-1 gap-1">
                <button class="text-white text-xs bg-primary-600 hover:bg-primary-700 rounded px-1.5 py-0.5 flex-1" @click.stop="insertAttachmentToDescription(att)">插入</button>
                <button class="text-white text-xs bg-red-600 hover:bg-red-700 rounded px-1.5 py-0.5 flex-1" @click.stop="promptDeleteAttachment(att)">删除</button>
              </div>
            </div>
          </div>

          <!-- 非图片附件：列表 -->
          <div v-if="fileAttachments.length" class="space-y-1">
            <div
              v-for="att in fileAttachments"
              :key="att.id"
              class="flex items-center gap-2 px-2 py-1.5 rounded-lg bg-gray-50 dark:bg-gray-800 group"
            >
              <UIcon name="i-heroicons-document" class="w-4 h-4 text-gray-400 shrink-0" />
              <span class="text-xs text-gray-700 dark:text-gray-300 truncate flex-1" :title="att.file_name">{{ att.file_name }}</span>
              <a :href="att.file_url" :download="att.file_name" target="_blank" class="text-xs text-blue-500 hover:text-blue-600 shrink-0">下载</a>
              <button class="text-xs text-red-500 hover:text-red-600 shrink-0 opacity-0 group-hover:opacity-100" @click.stop="deleteAttachment(att.id)">删除</button>
            </div>
          </div>

          <p v-if="!attachments.length" class="text-xs text-gray-400 dark:text-gray-500">暂无附件</p>
        </div>

        <div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 p-5 space-y-3">
          <h3 class="text-sm font-semibold text-gray-900 dark:text-gray-100">关联仓库</h3>
          <div v-if="issueRepo" class="flex items-center gap-2">
            <UIcon name="i-heroicons-code-bracket" class="w-4 h-4 text-gray-400" />
            <NuxtLink :to="`/app/repos/${issueRepo.id}`" class="text-sm text-blue-600 dark:text-blue-400 hover:underline">
              {{ issueRepo.full_name }}
            </NuxtLink>
            <UBadge v-if="issueRepo.clone_status === 'cloned'" color="success" variant="subtle" size="xs">已克隆</UBadge>
            <UBadge v-else-if="issueRepo.clone_status === 'cloning'" color="warning" variant="subtle" size="xs">克隆中</UBadge>
            <UBadge v-else color="neutral" variant="subtle" size="xs">未克隆</UBadge>
          </div>
          <p v-else class="text-sm text-gray-400 dark:text-gray-500">未关联仓库</p>
        </div>

        <div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 p-5 space-y-3">
          <div class="flex items-center justify-between">
            <h3 class="text-sm font-semibold text-gray-900 dark:text-gray-100">GitHub 关联</h3>
            <ServiceStatusDot :online="isOnline('github')" />
          </div>

          <!-- 已关联的 GitHub Issues -->
          <div v-if="issue.github_issues?.length" class="space-y-2">
            <div v-for="gh in issue.github_issues" :key="gh.id" class="flex items-center justify-between bg-gray-50 dark:bg-gray-800 rounded-lg px-3 py-2">
              <div class="min-w-0 flex-1">
                <div class="flex items-center space-x-2">
                  <UBadge :color="gh.state === 'open' ? 'success' : 'neutral'" variant="subtle" size="xs">{{ gh.state }}</UBadge>
                  <span class="text-xs text-gray-400 dark:text-gray-500">{{ gh.repo_full_name }}#{{ gh.github_id }}</span>
                </div>
                <p class="text-sm text-gray-900 dark:text-gray-100 truncate mt-0.5">{{ gh.title }}</p>
              </div>
              <UButton icon="i-heroicons-x-mark" variant="ghost" color="neutral" size="xs" @click="unlinkGitHubIssue(gh.id)" />
            </div>
          </div>
          <p v-else class="text-sm text-gray-400 dark:text-gray-500">暂无关联记录</p>

          <!-- 操作按钮 -->
          <div class="flex flex-col gap-2 pt-1">
            <UButton size="xs" variant="outline" color="neutral" icon="i-heroicons-plus" @click="showCreateGH = true" block>
              创建 GitHub Issue
            </UButton>
            <UButton size="xs" variant="outline" color="neutral" icon="i-heroicons-link" @click="showLinkGH = true" block>
              关联已有 Issue
            </UButton>
          </div>
        </div>
      </div>
    </div>

    <!-- 创建 GitHub Issue 弹窗 -->
    <UModal v-model:open="showCreateGH" title="创建 GitHub Issue" :ui="{ width: 'sm:max-w-md' }">
      <template #content>
        <div class="modal-form">
          <div class="modal-header">
            <h3>创建 GitHub Issue</h3>
            <UButton icon="i-heroicons-x-mark" variant="ghost" color="neutral" size="sm" @click="showCreateGH = false" />
          </div>
          <div class="modal-body">
            <p class="text-sm text-gray-500 dark:text-gray-400">将根据当前问题的标题和描述在 GitHub 仓库创建 Issue，并自动关联。</p>
            <div class="form-row">
              <label>目标仓库 <span class="text-red-400">*</span></label>
              <USelect v-model="ghCreateRepo" :items="repoOptions" placeholder="选择仓库" value-key="value" />
            </div>
            <p v-if="ghCreateError" class="text-sm text-red-500">{{ ghCreateError }}</p>
          </div>
          <div class="modal-footer">
            <UButton variant="outline" color="neutral" @click="showCreateGH = false">取消</UButton>
            <UButton :loading="ghCreating" @click="handleCreateGH">创建</UButton>
          </div>
        </div>
      </template>
    </UModal>

    <!-- 删除附件确认弹窗 -->
    <UModal v-model:open="showDeleteAttachmentConfirm">
      <template #content>
        <div class="modal-form">
          <div class="modal-header">
            <h3>删除附件</h3>
            <UButton icon="i-heroicons-x-mark" variant="ghost" color="neutral" size="sm" @click="showDeleteAttachmentConfirm = false" />
          </div>
          <div class="modal-body space-y-2">
            <p class="text-sm text-gray-700 dark:text-gray-300">
              确认删除附件 <span class="font-medium">{{ pendingDeleteAttachment?.file_name }}</span>？
            </p>
            <p class="text-sm text-gray-500 dark:text-gray-400">是否同时移除描述中的引用？</p>
          </div>
          <div class="modal-footer">
            <UButton variant="outline" color="neutral" @click="showDeleteAttachmentConfirm = false">取消</UButton>
            <UButton color="error" variant="outline" @click="() => { deleteAttachment(pendingDeleteAttachment!.id, false); showDeleteAttachmentConfirm = false }">仅删除文件</UButton>
            <UButton color="error" @click="() => { deleteAttachment(pendingDeleteAttachment!.id, true); showDeleteAttachmentConfirm = false }">删除并移除引用</UButton>
          </div>
        </div>
      </template>
    </UModal>

    <!-- 关联已有 GitHub Issue 弹窗 -->
    <UModal v-model:open="showLinkGH" title="关联 GitHub Issue" :ui="{ width: 'sm:max-w-lg' }">
      <template #content>
        <div class="modal-form">
          <div class="modal-header">
            <h3>关联 GitHub Issue</h3>
            <UButton icon="i-heroicons-x-mark" variant="ghost" color="neutral" size="sm" @click="showLinkGH = false" />
          </div>
          <div class="modal-body">
            <div class="form-row">
              <label>筛选仓库</label>
              <USelect v-model="ghLinkRepoFilter" :items="[{ label: '全部', value: '' }, ...repoOptions]" value-key="value" />
            </div>
            <div class="max-h-60 overflow-y-auto space-y-1 mt-2">
              <div v-for="gh in availableGHIssues" :key="gh.id" class="flex items-center space-x-2 px-2 py-1.5 rounded hover:bg-gray-50 dark:hover:bg-gray-800 cursor-pointer" @click="toggleGHSelection(gh.id)">
                <UCheckbox :model-value="ghSelectedIds.includes(gh.id)" />
                <div class="min-w-0 flex-1">
                  <span class="text-xs text-gray-400 dark:text-gray-500">{{ gh.repo_full_name }}#{{ gh.github_id }}</span>
                  <p class="text-sm text-gray-900 dark:text-gray-100 truncate">{{ gh.title }}</p>
                </div>
                <UBadge :color="gh.state === 'open' ? 'success' : 'neutral'" variant="subtle" size="xs">{{ gh.state }}</UBadge>
              </div>
              <p v-if="!availableGHIssues.length" class="text-sm text-gray-400 dark:text-gray-500 text-center py-4">没有可关联的 GitHub Issue</p>
            </div>
          </div>
          <div class="modal-footer">
            <UButton variant="outline" color="neutral" @click="showLinkGH = false">取消</UButton>
            <UButton :disabled="!ghSelectedIds.length" :loading="ghLinking" @click="handleLinkGH">关联 ({{ ghSelectedIds.length }})</UButton>
          </div>
        </div>
      </template>
    </UModal>
  </div>

  <div v-else class="text-center py-20 text-sm text-gray-400 dark:text-gray-500">问题不存在</div>
</template>

<script setup lang="ts">
definePageMeta({ layout: 'default' })

const { api } = useApi()
const route = useRoute()
const { isOnline } = useServiceStatus()

const loading = ref(true)
const issue = ref<any>(null)
const aiAnalyzing = ref(false)
let pollTimer: ReturnType<typeof setInterval> | null = null
const analyses = ref<any[]>([])

async function fetchAnalyses() {
  if (!issue.value?.id) return
  analyses.value = await api<any[]>(`/api/issues/${issue.value.id}/analyses/`).catch(() => []) || []
}

function fieldLabel(field: string) {
  const labels: Record<string, string> = { cause: '原因分析', solution: '解决方案', remark: '备注' }
  return labels[field] || field
}

import MarkdownIt from 'markdown-it'
const md = new MarkdownIt({ html: false, linkify: true })
function renderMarkdown(text: string) {
  if (!text) return ''
  return md.render(text)
}

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})
const users = ref<any[]>([])
const labelItems = ref<string[]>([])
const repos = ref<any[]>([])
const allGHIssues = ref<any[]>([])
const descriptionEditor = ref<{ setMode: (m: 'edit' | 'preview') => void } | null>(null)

const isNewIssue = computed(() => !issue.value?.description && !issue.value?.title)

// 删除附件确认
const showDeleteAttachmentConfirm = ref(false)
const pendingDeleteAttachment = ref<{ id: string; file_url: string; file_name: string } | null>(null)

// GitHub 创建
const showCreateGH = ref(false)
const ghCreateRepo = ref('')
const ghCreating = ref(false)
const ghCreateError = ref('')

// GitHub 关联
const showLinkGH = ref(false)
const ghLinkRepoFilter = ref('')
const ghSelectedIds = ref<number[]>([])
const ghLinking = ref(false)

const repoOptions = computed(() => repos.value.map(r => ({ label: r.full_name, value: String(r.id) })))
const issueRepo = computed(() => {
  if (!issue.value?.repo) return null
  return repos.value.find(r => r.id === issue.value.repo) || null
})

const linkedGHIds = computed(() => new Set((issue.value?.github_issues || []).map((g: any) => g.id)))

const availableGHIssues = computed(() => {
  return allGHIssues.value.filter(gh => {
    if (linkedGHIds.value.has(gh.id)) return false
    if (ghLinkRepoFilter.value && String(gh.repo) !== ghLinkRepoFilter.value) return false
    return true
  })
})

const form = ref({
  title: '',
  description: '',
  labels: [] as string[],
  assignee: '_none',
  helpers: [] as string[],
  remark: '',
  cause: '',
  solution: '',
  estimated_completion: '',
  actual_hours: '',
})

const priorityItems = [
  { label: 'P0', value: 'P0', activeClass: 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300' },
  { label: 'P1', value: 'P1', activeClass: 'bg-orange-100 text-orange-700 dark:bg-orange-900 dark:text-orange-300' },
  { label: 'P2', value: 'P2', activeClass: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300' },
  { label: 'P3', value: 'P3', activeClass: 'bg-gray-200 text-gray-600 dark:bg-gray-700 dark:text-gray-300' },
]
const statusItems = [
  { label: '待处理', value: '待处理', activeClass: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300' },
  { label: '进行中', value: '进行中', activeClass: 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300' },
  { label: '已解决', value: '已解决', activeClass: 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300' },
  { label: '已关闭', value: '已关闭', activeClass: 'bg-gray-200 text-gray-600 dark:bg-gray-700 dark:text-gray-300' },
]
const assigneeItems = computed(() => [
  { label: '无', value: '_none' },
  ...users.value.map(u => ({ label: u.name || u.username, value: String(u.id) })),
])
const helperItems = computed(() =>
  users.value.map(u => ({ label: u.name || u.username, value: String(u.id) }))
)

const savedForm = ref<typeof form.value>({ ...form.value })
const savingField = ref<string | null>(null)

function isFieldDirty(field: keyof typeof form.value) {
  return JSON.stringify(form.value[field]) !== JSON.stringify(savedForm.value[field])
}

function populateForm(data: any) {
  form.value = {
    title: data.title || '',
    description: data.description || '',
    labels: data.labels || [],
    assignee: data.assignee ? String(data.assignee) : '_none',
    helpers: (data.helpers || []).map(String),
    remark: data.remark || '',
    cause: data.cause || '',
    solution: data.solution || '',
    estimated_completion: data.estimated_completion || '',
    actual_hours: data.actual_hours != null ? String(data.actual_hours) : '',
  }
  savedForm.value = JSON.parse(JSON.stringify(form.value))
}

async function fetchIssue() {
  issue.value = await api<any>(`/api/issues/${route.params.id}/`)
  populateForm(issue.value)
}

async function triggerAIAnalysis() {
  if (aiAnalyzing.value) return // prevent double-click
  aiAnalyzing.value = true
  try {
    const res = await api<any>(`/api/issues/${route.params.id}/ai-analyze/`, {
      method: 'POST',
    })
    pollAnalysisStatus(res.analysis_id)
  } catch (e: any) {
    const status = e.status || e.statusCode
    if (status === 409) {
      // Already running (likely auto-triggered), poll it
      const analysisId = e.data?.analysis_id
      if (analysisId) {
        pollAnalysisStatus(analysisId)
      } else {
        aiAnalyzing.value = false
      }
    } else {
      aiAnalyzing.value = false
    }
  }
}

function pollAnalysisStatus(analysisId: number | undefined) {
  if (!analysisId) { aiAnalyzing.value = false; return }
  let failCount = 0
  pollTimer = setInterval(async () => {
    try {
      const res = await api<any>(`/api/ai/analysis/${analysisId}/status/`)
      failCount = 0
      if (res.status === 'done' || res.status === 'failed') {
        clearInterval(pollTimer!)
        aiAnalyzing.value = false
        await fetchAnalyses()
      }
    } catch {
      failCount++
      if (failCount >= 3) {
        clearInterval(pollTimer!)
        aiAnalyzing.value = false
      }
    }
  }, 3000)
}



// 文本输入框：显示保存按钮，点击后保存
async function saveField(field: keyof typeof form.value) {
  if (!issue.value) return
  savingField.value = field
  try {
    const body: Record<string, any> = {}
    const val = form.value[field]
    if (field === 'actual_hours') body.actual_hours = val ? Number(val) : null
    else body[field] = val
    await api(`/api/issues/${issue.value.id}/`, { method: 'PATCH', body })
    issue.value = await api<any>(`/api/issues/${route.params.id}/`)
    populateForm(issue.value)
    if (field === 'description') descriptionEditor.value?.setMode('preview')
  } catch (e) {
    console.error(`Save ${field} failed:`, e)
  } finally {
    savingField.value = null
  }
}

// 下拉/胶囊/日期：直接保存
async function autoSave(field: string, rawValue: any) {
  if (!issue.value) return
  let value = rawValue
  if (field === 'assignee') value = rawValue === '_none' ? null : rawValue
  if (field === 'helpers') value = (rawValue as string[]).map(Number)
  if (field === 'estimated_completion') value = rawValue || null
  try {
    await api(`/api/issues/${issue.value.id}/`, { method: 'PATCH', body: { [field]: value } })
    issue.value = await api<any>(`/api/issues/${route.params.id}/`)
    populateForm(issue.value)
  } catch (e) {
    console.error(`Auto-save ${field} failed:`, e)
  }
}

function toggleLabel(lbl: string) {
  const idx = form.value.labels.indexOf(lbl)
  if (idx >= 0) form.value.labels.splice(idx, 1)
  else form.value.labels.push(lbl)
  autoSave('labels', [...form.value.labels])
}

// 优先级/状态胶囊直接保存
async function updateField(field: string, value: string) {
  await autoSave(field, value)
}

// 状态胶囊点击处理（已解决 -> 已关闭 时检查 GitHub）
function handleStatusClick(newStatus: string) {
  if (newStatus === '已关闭') {
    const hasOpenGH = issue.value?.github_issues?.some((gh: any) => gh.state === 'open')
    if (hasOpenGH) {
      closeWithGitHub()
      return
    }
  }
  updateField('status', newStatus)
}

async function closeWithGitHub() {
  if (!issue.value) return
  try {
    await api(`/api/issues/${issue.value.id}/close-with-github/`, { method: 'POST' })
    issue.value = await api<any>(`/api/issues/${route.params.id}/`)
    populateForm(issue.value)
  } catch (e) {
    console.error('Close failed:', e)
  }
}

function toggleGHSelection(id: number) {
  const idx = ghSelectedIds.value.indexOf(id)
  if (idx >= 0) ghSelectedIds.value.splice(idx, 1)
  else ghSelectedIds.value.push(id)
}

async function handleCreateGH() {
  if (!ghCreateRepo.value) {
    ghCreateError.value = '请选择仓库'
    return
  }
  ghCreating.value = true
  ghCreateError.value = ''
  try {
    await api(`/api/issues/${issue.value.id}/github-create/`, {
      method: 'POST',
      body: { repo: ghCreateRepo.value },
    })
    showCreateGH.value = false
    ghCreateRepo.value = ''
    issue.value = await api<any>(`/api/issues/${route.params.id}/`)
    populateForm(issue.value)
  } catch (e: any) {
    ghCreateError.value = e?.data?.detail || 'GitHub 创建失败'
  } finally {
    ghCreating.value = false
  }
}

async function handleLinkGH() {
  if (!ghSelectedIds.value.length) return
  ghLinking.value = true
  try {
    await api(`/api/issues/${issue.value.id}/github-link/`, {
      method: 'POST',
      body: { github_issue_ids: ghSelectedIds.value },
    })
    showLinkGH.value = false
    ghSelectedIds.value = []
    issue.value = await api<any>(`/api/issues/${route.params.id}/`)
    populateForm(issue.value)
  } catch (e) {
    console.error('Link failed:', e)
  } finally {
    ghLinking.value = false
  }
}

async function unlinkGitHubIssue(ghId: number) {
  try {
    await api(`/api/issues/${issue.value.id}/github-link/`, {
      method: 'DELETE',
      body: { github_issue_ids: [ghId] },
    })
    issue.value = await api<any>(`/api/issues/${route.params.id}/`)
    populateForm(issue.value)
  } catch (e) {
    console.error('Unlink failed:', e)
  }
}

async function fetchGHIssues() {
  allGHIssues.value = await api<any[]>('/api/repos/github-issues/').catch(() => []) || []
}

onMounted(async () => {
  const [issueData, usersData, settingsData, reposData] = await Promise.all([
    api<any>(`/api/issues/${route.params.id}/`).catch(() => null),
    api<any[]>('/api/users/').catch(() => []),
    api<any>('/api/settings/').catch(() => ({ labels: [] })),
    api<any[]>('/api/repos/').catch(() => []),
  ])
  issue.value = issueData
  users.value = usersData?.results || usersData || []
  labelItems.value = settingsData?.labels || []
  repos.value = reposData?.results || reposData || []
  if (issueData) populateForm(issueData)
  loading.value = false
  // 异步加载 GitHub Issues 列表（用于关联弹窗）
  fetchGHIssues()
  // 检查是否有正在运行的 AI 分析，恢复轮询
  checkRunningAnalysis()
  fetchAnalyses()
})

async function checkRunningAnalysis() {
  if (!issue.value?.id) return
  try {
    const res = await api<any>(`/api/issues/${issue.value.id}/ai-status/`)
    if (res?.analysis_id && res?.status === 'running') {
      aiAnalyzing.value = true
      pollAnalysisStatus(res.analysis_id)
    }
  } catch {
    // No running analysis endpoint or no analysis — that's fine
  }
}

// 关联附件
const attachmentInputRef = ref<HTMLInputElement | null>(null)
const attachments = computed(() => (issue.value as any)?.attachments ?? [])
const imageAttachments = computed(() => attachments.value.filter((a: any) => a.mime_type?.startsWith('image/')))
const fileAttachments = computed(() => attachments.value.filter((a: any) => !a.mime_type?.startsWith('image/')))

async function handleUploadComplete(uploaded: { url: string; filename: string; id: string }) {
  if (!issue.value?.id) return
  const { api } = useApi()
  try {
    await api(`/api/issues/${issue.value.id}/attachments/`, {
      method: 'POST',
      body: { attachment_id: uploaded.id },
    })
    issue.value = await api<any>(`/api/issues/${issue.value.id}/`)
  } catch {
    // 绑定失败静默处理
  }
}

async function handleAttachmentSelect(e: Event) {
  const input = e.target as HTMLInputElement
  const files = Array.from(input.files || [])
  input.value = ''
  const { api } = useApi()
  for (const file of files) {
    try {
      const formData = new FormData()
      formData.append('file', file)
      const res = await api<{ url: string; filename: string; id: string }>('/api/tools/upload/image/', {
        method: 'POST',
        body: formData,
      })
      await handleUploadComplete(res)
    } catch {
      // 上传失败静默处理
    }
  }
}

function promptDeleteAttachment(att: { id: string; file_url: string; file_name: string }) {
  pendingDeleteAttachment.value = att
  showDeleteAttachmentConfirm.value = true
}

async function deleteAttachment(attachmentId: string, removeFromDescription = false) {
  const { api } = useApi()
  try {
    await api(`/api/tools/attachments/${attachmentId}/`, { method: 'DELETE' })
    if (issue.value) {
      const att = (issue.value as any).attachments.find((a: any) => a.id === attachmentId)
      if (removeFromDescription && att) {
        removeAttachmentFromDescription(att.file_url)
      }
      ;(issue.value as any).attachments = (issue.value as any).attachments.filter((a: any) => a.id !== attachmentId)
    }
  } catch {
    // 删除失败静默处理
  }
}

function removeAttachmentFromDescription(fileUrl: string) {
  if (!form.value.description) return
  const escaped = fileUrl.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  form.value.description = form.value.description
    .replace(new RegExp(`!\\[[^\\]]*\\]\\(${escaped}\\)`, 'g'), '')
    .replace(/\n{3,}/g, '\n\n')
    .trim()
}

function insertAttachmentToDescription(attachment: any) {
  form.value.description = (form.value.description || '') + `\n![${attachment.file_name}](${attachment.file_url})`
}
</script>

<style scoped>
.form-row { display: flex; flex-direction: column; gap: 0.375rem; }
.form-row label { font-size: 0.8125rem; font-weight: 500; color: #374151; }
:root.dark .form-row label { color: #9ca3af; }
.form-row :deep(input),
.form-row :deep(textarea),
.form-row :deep(select),
.form-row :deep(button[role="combobox"]),
.form-row :deep([data-part="trigger"]) { width: 100% !important; }
.form-grid-2 { display: grid; grid-template-columns: 1fr; gap: 1rem; }
@media (min-width: 768px) {
  .form-grid-2 { grid-template-columns: 1fr 1fr; }
}
.modal-form { padding: 1.5rem 2rem; }
.modal-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 1.5rem; }
.modal-header h3 { font-size: 1.125rem; font-weight: 600; color: #111827; }
:root.dark .modal-header h3 { color: #f3f4f6; }
.modal-body { display: flex; flex-direction: column; gap: 1rem; }
.modal-footer { display: flex; justify-content: flex-end; gap: 0.75rem; margin-top: 1.5rem; padding-top: 1rem; border-top: 1px solid #f3f4f6; }
:root.dark .modal-footer { border-top-color: #374151; }
.ai-progress-bar {
  width: 30%;
  animation: ai-progress 2s ease-in-out infinite;
}
@keyframes ai-progress {
  0% { margin-left: 0%; width: 20%; }
  50% { margin-left: 40%; width: 40%; }
  100% { margin-left: 80%; width: 20%; }
}
</style>
