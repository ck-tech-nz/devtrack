<template>
  <div
    class="ai-wizard"
    :class="{
      'ai-wizard--chat': inChatMode,
      'ai-wizard--draft-pending': draftPending,
    }"
  >
    <h2 v-if="!inChatMode" class="hero-title">有什么我可以帮你的？</h2>

    <!-- 对话 thread — chat 模式撑满上方空间, composer 自然贴底 -->
    <div v-if="inChatMode" ref="threadEl" class="thread">
      <!-- 用户消息 -->
      <div class="msg msg--user">
        <div v-if="sentAttachments.length" class="msg-attach-row">
          <button
            v-for="att in sentAttachments"
            :key="att.id"
            type="button"
            class="msg-attach"
            :class="{ 'msg-attach--image': isImage(att.file_name) }"
            :title="isImage(att.file_name) ? `预览 ${att.file_name}` : att.file_name"
            :disabled="!isImage(att.file_name)"
            @click="isImage(att.file_name) && openPreview(att)"
          >
            <img v-if="isImage(att.file_name)" :src="att.file_url" :alt="att.file_name" />
            <template v-else>
              <UIcon name="i-heroicons-document" class="w-3.5 h-3.5" />
              <span class="msg-attach-name">{{ att.file_name }}</span>
            </template>
          </button>
        </div>
        <div v-if="sentDescription" class="msg-bubble">{{ sentDescription }}</div>
      </div>

      <!-- AI 第一条回复: 思考过程 (始终显示, draft 出来后变 done) -->
      <div class="msg msg--ai">
        <div class="msg-brand">
          <span class="msg-brand-mark">
            <UIcon name="i-heroicons-sparkles" class="w-3 h-3" />
          </span>
          <span class="msg-brand-name">DevTrakr</span>
          <span v-if="isThinking" class="msg-brand-status">
            <span class="brand-pulse" /> 正在思考
          </span>
          <span v-else-if="thinkingDone" class="msg-brand-status msg-brand-status--done">
            已分析
          </span>
        </div>

        <div class="msg-thinking">
          <div
            v-for="s in wizard.steps.value"
            :key="s.step"
            class="think-line"
            :class="`think-line--${s.status}`"
          >
            <UIcon v-if="s.status === 'done'" name="i-heroicons-check-circle" class="w-3.5 h-3.5 think-icon think-icon--done" />
            <UIcon v-else-if="s.status === 'error'" name="i-heroicons-exclamation-circle" class="w-3.5 h-3.5 think-icon think-icon--error" />
            <span v-else class="think-dot" />
            <span class="think-label">{{ s.label }}</span>
            <span v-if="s.status === 'running'" class="think-caret" aria-hidden="true">▍</span>
          </div>
        </div>

        <div v-if="wizard.errorMessage.value" class="msg-error">
          <UIcon name="i-heroicons-exclamation-triangle" class="w-3.5 h-3.5" />
          <span>{{ wizard.errorMessage.value }}</span>
        </div>

        <div v-if="wizard.errorMessage.value" class="msg-actions">
          <button type="button" class="msg-action msg-action--primary" @click="onRetry">重试</button>
          <button type="button" class="msg-action" @click="onBackToDescribe">重新描述</button>
        </div>
      </div>

      <!-- AI 第二条回复: 草稿 (左对齐, 作为对话延续) -->
      <div v-if="currentStep === 3 && wizard.draft.value" class="msg msg--ai msg--ai-draft">
        <div class="msg-brand">
          <span class="msg-brand-mark">
            <UIcon name="i-heroicons-sparkles" class="w-3 h-3" />
          </span>
          <span class="msg-brand-name">DevTrakr</span>
          <span class="msg-brand-status msg-brand-status--draft">
            草稿已就绪
          </span>
        </div>
        <div class="msg-draft-card">
          <StepDraft
            :draft="wizard.draft.value"
            :projects="projects"
            :initial-project-id="lastAnalyzedProject"
            :modules="modules"
            :users="users"
            :valid-labels="validLabels"
            :attachment-ids="lastAttachmentIds"
            :original-input="lastOriginalInput"
            :submitting="submitting"
            :submit-error="submitError"
            :success-issue-id="successIssueId"
            :success-assignee="successAssignee"
            @submit="onSubmit"
            @back="onBackToDescribe"
            @reset="onReset"
          />
        </div>
      </div>
    </div>

    <!-- Composer (始终渲染, chat 模式下钉在 wizard 底部) -->
    <div class="composer-slot">
      <StepDescribe
        ref="describeRef"
        :projects="projects"
        :default-project-id="defaultProjectId"
        :analyzing="currentStep === 2"
        @analyze="onAnalyze"
        @cancel="onBackToDescribe"
      />
    </div>

    <!-- thread 内图片缩略图的预览弹窗 -->
    <UModal v-model:open="previewOpen" :ui="{ content: 'sm:max-w-4xl' }">
      <template #content>
        <div class="preview-modal">
          <div class="preview-header">
            <span class="preview-title" :title="previewAttachment?.file_name">{{ previewAttachment?.file_name }}</span>
            <UButton icon="i-heroicons-x-mark" variant="ghost" color="neutral" size="sm" @click="previewOpen = false" />
          </div>
          <div class="preview-body" @click.self="previewOpen = false">
            <img v-if="previewAttachment" :src="previewAttachment.file_url" :alt="previewAttachment.file_name" />
          </div>
        </div>
      </template>
    </UModal>
  </div>
</template>

<script setup lang="ts">
import StepDescribe, { type AttachmentRef } from './AiIssueWizard/StepDescribe.vue'
import StepDraft from './AiIssueWizard/StepDraft.vue'

const emit = defineEmits<{ created: [issueId: number] }>()

const { api } = useApi()
const { user } = useAuth()

const defaultProjectId = computed(() => user.value?.default_project?.id || null)

const projects = ref<{ id: string; name: string }[]>([])
const modules = ref<string[]>([])
const users = ref<{ id: string; name: string }[]>([])
const validLabels = ref<string[]>([])
const lastAnalyzedProject = ref<string>('')
const lastAttachmentIds = ref<string[]>([])
const lastOriginalInput = ref<string>('')

// thread 中渲染的用户消息快照
const sentDescription = ref<string>('')
const sentAttachments = ref<AttachmentRef[]>([])

// 缩略图点击预览
const previewOpen = ref(false)
const previewAttachment = ref<AttachmentRef | null>(null)
function openPreview(att: AttachmentRef) {
  previewAttachment.value = att
  previewOpen.value = true
}

const describeRef = ref<InstanceType<typeof StepDescribe> | null>(null)
const threadEl = ref<HTMLElement | null>(null)

const wizard = useAiWizard()
const submitting = ref(false)
const submitError = ref('')
const successIssueId = ref<number | null>(null)
const successAssignee = ref<string | null>(null)

const currentStep = computed(() => {
  if (successIssueId.value) return 3
  if (wizard.state.value === 'idle') return 1
  if (wizard.state.value === 'analyzing' || wizard.state.value === 'error') return 2
  if (wizard.state.value === 'drafting') return 3
  return 1
})

// chat 模式: 用户已发出过描述, 应该把上方空间留给 thread
const inChatMode = computed(() => currentStep.value >= 2 || !!sentDescription.value)

// 草稿待定 (尚未点"提交 Issue") 期间, composer 钉在视口底端,
// 让用户一边滚动浏览 thread, 一边随时能继续对话/取消
const draftPending = computed(() => inChatMode.value && !successIssueId.value)

const isThinking = computed(() => wizard.state.value === 'analyzing')
const thinkingDone = computed(() =>
  !wizard.errorMessage.value
  && wizard.state.value !== 'analyzing'
  && wizard.steps.value.some(s => s.status === 'done'),
)

function isImage(name: string): boolean {
  return /\.(png|jpe?g|gif|webp|bmp|svg)$/i.test(name || '')
}

onMounted(async () => {
  const [projectData, settingsData, usersData] = await Promise.all([
    api<any>('/api/projects/').catch(() => ({ results: [] })),
    api<any>('/api/settings/').catch(() => ({ modules: [] })),
    api<any[]>('/api/users/choices/').catch(() => []),
  ])
  projects.value = (projectData.results || projectData || []).map((p: any) => ({ id: String(p.id), name: p.name }))
  modules.value = settingsData.modules || []
  validLabels.value = Object.keys(settingsData.labels || {})
  users.value = (usersData || []).map((u: any) => ({ id: String(u.id), name: u.name || u.username }))
})

function onAnalyze(payload: { description: string; project: string; attachments: AttachmentRef[] }) {
  sentDescription.value = payload.description
  sentAttachments.value = payload.attachments
  lastAnalyzedProject.value = payload.project
  lastAttachmentIds.value = payload.attachments.map(a => a.id)
  lastOriginalInput.value = payload.description
  wizard.start({
    description: payload.description,
    project: payload.project,
    attachment_ids: lastAttachmentIds.value,
  })
}

function onRetry() {
  // 把用户当前消息再发一次 (不清空 thread, 也不让 composer 失焦)
  if (!sentDescription.value || !lastAnalyzedProject.value) return
  wizard.start({
    description: sentDescription.value,
    project: lastAnalyzedProject.value,
    attachment_ids: lastAttachmentIds.value,
  })
}

function onBackToDescribe() {
  // 把已发出的内容还原到 composer, 让用户继续编辑; 然后清空 thread
  if (describeRef.value) {
    describeRef.value.setText(sentDescription.value)
    describeRef.value.setAttachments(sentAttachments.value)
  }
  sentDescription.value = ''
  sentAttachments.value = []
  wizard.reset()
  successIssueId.value = null
  successAssignee.value = null
  submitError.value = ''
}

function onReset() {
  sentDescription.value = ''
  sentAttachments.value = []
  wizard.reset()
  successIssueId.value = null
  successAssignee.value = null
  submitError.value = ''
}

async function onSubmit(body: any) {
  submitting.value = true
  submitError.value = ''
  try {
    const created = await api<any>('/api/issues/', { method: 'POST', body, format: 'json' })
    successIssueId.value = Number(created.id)
    successAssignee.value = created.assignee != null ? String(created.assignee) : null
    emit('created', created.id)
  } catch (e: any) {
    const data = e?.data || e?.response?._data
    submitError.value = (data && typeof data === 'object') ? JSON.stringify(data) : (e?.message || '创建失败')
  } finally {
    submitting.value = false
  }
}

// 每次有新消息追加, 把 thread 滚到底部 (草稿出现时一定要让用户看到)
watch([
  () => currentStep.value,
  () => wizard.steps.value.map(s => s.status).join(','),
  () => wizard.errorMessage.value,
], async () => {
  await nextTick()
  if (threadEl.value) threadEl.value.scrollTop = threadEl.value.scrollHeight
})

onBeforeUnmount(() => {
  wizard.abort()
})
</script>

<style scoped>
.ai-wizard {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
  padding: 1rem 0;
}

/* chat 模式: 上方留对话区, composer 在 draft-pending 期间 sticky 钉视口底端 */
.ai-wizard--chat {
  gap: 1rem;
}

.hero-title {
  font-size: 1.875rem;
  font-weight: 600;
  color: #111827;
  text-align: center;
  margin: 1rem 0 0.5rem;
}
:root.dark .hero-title { color: #f3f4f6; }

/* ---------- Thread ---------- */
/* thread 自然增高, 跟 page 一起 scroll; composer 用 sticky 钉视口底端 */
.thread {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
  padding: 0.5rem 0.25rem;
}

.msg { display: flex; flex-direction: column; gap: 0.5rem; }

.msg--user {
  align-items: flex-end;
  animation: msg-rise 0.32s ease both;
}
.msg--ai {
  align-items: flex-start;
  animation: msg-rise 0.32s ease both;
  animation-delay: 80ms;
}
.msg--ai-draft {
  animation-delay: 0ms;
  /* 草稿是延后出现的, 自然进入即可 */
}
@keyframes msg-rise {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

/* ---------- 用户气泡 ---------- */
.msg-bubble {
  max-width: min(40rem, 90%);
  padding: 0.625rem 0.875rem;
  background-color: #f3f4f6;
  color: #1f2937;
  border-radius: 1rem 1rem 0.25rem 1rem;
  font-size: 0.875rem;
  line-height: 1.55;
  white-space: pre-wrap;
  word-break: break-word;
}
:root.dark .msg-bubble { background-color: #1f2937; color: #e5e7eb; }

.msg-attach-row {
  display: flex; flex-wrap: wrap; justify-content: flex-end;
  gap: 0.375rem;
  max-width: min(40rem, 90%);
}
.msg-attach {
  display: inline-flex; align-items: center; gap: 0.25rem;
  padding: 0;
  border: 0;
  border-radius: 0.5rem;
  background: transparent;
  overflow: hidden;
  cursor: default;
}
.msg-attach--image {
  width: 3.5rem;
  height: 3.5rem;
  border: 1px solid #e5e7eb;
  background-color: #ffffff;
  cursor: zoom-in;
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}
.msg-attach--image:hover {
  transform: translateY(-1px);
  box-shadow: 0 2px 8px -2px rgba(0, 0, 0, 0.15);
}
:root.dark .msg-attach--image { border-color: #374151; background-color: #111827; }
.msg-attach--image img { width: 100%; height: 100%; object-fit: cover; display: block; }
.msg-attach:not(.msg-attach--image) {
  padding: 0.25rem 0.5rem;
  background-color: #f9fafb;
  border: 1px solid #e5e7eb;
  font-size: 0.75rem;
  color: #4b5563;
}
:root.dark .msg-attach:not(.msg-attach--image) {
  background-color: #1f2937; border-color: #374151; color: #d1d5db;
}
.msg-attach-name {
  max-width: 10rem;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}

/* ---------- AI 品牌标识 ---------- */
.msg-brand {
  display: flex; align-items: center; gap: 0.5rem;
  font-size: 0.75rem;
  color: #6b7280;
}
:root.dark .msg-brand { color: #9ca3af; }

.msg-brand-mark {
  width: 1.125rem; height: 1.125rem;
  border-radius: 0.375rem;
  display: inline-flex; align-items: center; justify-content: center;
  color: #ffffff;
  background: linear-gradient(135deg, #7c3aed, #9333ea);
  box-shadow: 0 1px 4px -1px rgba(124, 58, 237, 0.45);
}

.msg-brand-name {
  font-weight: 600;
  color: #374151;
  letter-spacing: -0.005em;
}
:root.dark .msg-brand-name { color: #e5e7eb; }

.msg-brand-status {
  display: inline-flex; align-items: center; gap: 0.375rem;
  font-size: 0.6875rem;
  color: #9ca3af;
  padding-left: 0.5rem;
  border-left: 1px solid #e5e7eb;
}
:root.dark .msg-brand-status { color: #6b7280; border-left-color: #374151; }
.msg-brand-status--done { color: #059669; }
:root.dark .msg-brand-status--done { color: #34d399; }
.msg-brand-status--draft { color: #7c3aed; }
:root.dark .msg-brand-status--draft { color: #c4b5fd; }

.brand-pulse {
  width: 0.4375rem; height: 0.4375rem;
  border-radius: 9999px;
  background-color: #7c3aed;
  animation: brand-pulse 1.2s ease-in-out infinite;
}
@keyframes brand-pulse {
  0%, 100% { opacity: 0.35; transform: scale(0.9); }
  50% { opacity: 1; transform: scale(1.15); box-shadow: 0 0 0 4px rgba(124, 58, 237, 0.12); }
}

/* ---------- 思考流 ---------- */
.msg-thinking {
  display: flex; flex-direction: column;
  gap: 0.5rem;
  padding-left: 1.625rem;
}

.think-line {
  display: flex; align-items: center; gap: 0.5rem;
  font-size: 0.8125rem;
  color: #6b7280;
}
.think-line--done { color: #059669; }
.think-line--error { color: #dc2626; }
.think-line--running { color: #4b5563; }
:root.dark .think-line { color: #9ca3af; }
:root.dark .think-line--running { color: #d1d5db; }
:root.dark .think-line--done { color: #34d399; }
:root.dark .think-line--error { color: #fca5a5; }

.think-icon--done { color: #10b981; }
.think-icon--error { color: #ef4444; }

.think-dot {
  width: 0.5rem; height: 0.5rem; border-radius: 9999px;
  background-color: #c4b5fd;
  animation: think-pulse 1s ease-in-out infinite alternate;
}
:root.dark .think-dot { background-color: #6d28d9; }
@keyframes think-pulse {
  from { opacity: 0.35; transform: scale(0.85); }
  to { opacity: 1; transform: scale(1.05); }
}

.think-caret {
  display: inline-block;
  color: #7c3aed;
  font-weight: 500;
  animation: caret-blink 0.9s steps(2, end) infinite;
  margin-left: -0.125rem;
  line-height: 1;
}
:root.dark .think-caret { color: #c4b5fd; }
@keyframes caret-blink {
  0%, 49% { opacity: 1; }
  50%, 100% { opacity: 0; }
}

/* ---------- 错误态 ---------- */
.msg-error {
  display: flex; align-items: center; gap: 0.375rem;
  margin-left: 1.625rem;
  padding: 0.5rem 0.75rem;
  font-size: 0.8125rem;
  color: #b91c1c;
  background-color: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 0.625rem;
}
:root.dark .msg-error {
  color: #fca5a5;
  background-color: rgba(239, 68, 68, 0.08);
  border-color: rgba(239, 68, 68, 0.25);
}

.msg-actions {
  display: flex; gap: 0.5rem;
  margin-left: 1.625rem;
}
.msg-action {
  padding: 0.3125rem 0.75rem;
  font-size: 0.75rem;
  border-radius: 0.5rem;
  border: 1px solid #e5e7eb;
  background-color: #ffffff;
  color: #4b5563;
  cursor: pointer;
  transition: background-color 0.15s, color 0.15s, border-color 0.15s;
}
.msg-action:hover { background-color: #f9fafb; color: #111827; }
:root.dark .msg-action {
  background-color: #1f2937; border-color: #374151; color: #d1d5db;
}
:root.dark .msg-action:hover { background-color: #111827; color: #f3f4f6; }
.msg-action--primary {
  background-color: #7c3aed; border-color: #7c3aed; color: #ffffff;
}
.msg-action--primary:hover {
  background-color: #6d28d9; border-color: #6d28d9; color: #ffffff;
}

/* ---------- 草稿卡片容器 ---------- */
/* StepDraft 在 thread 内只是预览, 用 :deep() 把内部尺寸全面紧凑化,
   宽度限制在 60% 且最大 36rem (~576px), 左对齐, 看不清/截断都无所谓 */
.msg-draft-card {
  width: min(60%, 36rem);
  margin-left: 0;
  animation: draft-rise 0.4s cubic-bezier(0.16, 1, 0.3, 1) both;
}
@keyframes draft-rise {
  from { opacity: 0; transform: translateY(12px); }
  to { opacity: 1; transform: translateY(0); }
}

/* 整体外壳收紧 */
.msg-draft-card :deep(.draft-wrap) {
  padding: 0.875rem 1rem 0.75rem;
  border-radius: 0.75rem;
  gap: 0.75rem;
}
.msg-draft-card :deep(.draft-header) {
  padding-bottom: 0.625rem;
}
.msg-draft-card :deep(.header-icon) {
  width: 1.375rem; height: 1.375rem;
  border-radius: 0.375rem;
}
.msg-draft-card :deep(.header-title) { font-size: 0.8125rem; }
.msg-draft-card :deep(.header-sub) { font-size: 0.6875rem; margin-top: 0.0625rem; }

/* 两栏布局: 收窄 sidebar, 整体 gap 压小 */
.msg-draft-card :deep(.draft-body) {
  grid-template-columns: minmax(0, 1fr) 12rem;
  gap: 1rem;
}

/* 左侧内容列 */
.msg-draft-card :deep(.content-col) { gap: 0.625rem; }
.msg-draft-card :deep(.issue-title-input) {
  font-size: 0.9375rem !important;
  padding: 0.375rem 0.5rem !important;
}
.msg-draft-card :deep(.issue-desc-input),
.msg-draft-card :deep(.issue-body-input) {
  font-size: 0.75rem !important;
  padding: 0.375rem 0.5rem !important;
}
.msg-draft-card :deep(.section) { gap: 0.25rem; padding-top: 0.125rem; }
.msg-draft-card :deep(.section-label) { font-size: 0.6875rem; }

/* MarkdownEditor 内嵌时压扁 */
.msg-draft-card :deep(.markdown-editor) {
  border-radius: 0.5rem;
}
.msg-draft-card :deep(.markdown-editor textarea) {
  min-height: 6.5rem !important;
  font-size: 0.75rem !important;
  padding: 0.625rem !important;
}
.msg-draft-card :deep(.markdown-editor .markdown-body) {
  min-height: 6.5rem !important;
  padding: 0.625rem 0.75rem !important;
  font-size: 0.75rem;
}
.msg-draft-card :deep(.markdown-editor img) {
  max-height: 9rem;
  width: auto;
}

/* 右侧 meta sidebar */
.msg-draft-card :deep(.meta-col) {
  padding-left: 0.875rem;
  gap: 0.625rem;
}
.msg-draft-card :deep(.meta-row) {
  grid-template-columns: 3.25rem 1fr;
  gap: 0.375rem;
}
.msg-draft-card :deep(.meta-label) { font-size: 0.6875rem; }

/* 底部 footer */
.msg-draft-card :deep(.footer) { padding-top: 0.625rem; }

/* AI 建议补充 callout */
.msg-draft-card :deep(.ai-suggest) { padding: 0.5rem 0.625rem; font-size: 0.6875rem; }

/* 窄屏: 单列堆叠时让 sidebar 不再固定宽度 */
@media (max-width: 768px) {
  .msg-draft-card { width: 100%; }
  .msg-draft-card :deep(.draft-body) { grid-template-columns: 1fr; }
}

/* ---------- Composer slot ---------- */
.composer-slot {
  flex-shrink: 0;
}

/* draft 未提交 (草稿待定) 期间, composer 钉在视口底端;
   page 自然 scroll, thread 在它之下滑过, 上沿渐变让 thread 视觉"消失"到 composer 后 */
.ai-wizard--draft-pending .composer-slot {
  position: sticky;
  bottom: 1rem;
  z-index: 10;
}
.ai-wizard--draft-pending .composer-slot::before {
  content: '';
  position: absolute;
  left: -0.25rem; right: -0.25rem;
  top: -1.25rem; height: 1.25rem;
  background: linear-gradient(to bottom, rgba(255, 255, 255, 0), rgba(255, 255, 255, 0.95));
  pointer-events: none;
}
:root.dark .ai-wizard--draft-pending .composer-slot::before {
  background: linear-gradient(to bottom, rgba(17, 24, 39, 0), rgba(17, 24, 39, 0.95));
}

/* ---------- 图片预览弹窗 ---------- */
.preview-modal {
  display: flex; flex-direction: column;
  max-height: 85vh;
  background-color: #ffffff;
  border-radius: 0.75rem;
  overflow: hidden;
}
:root.dark .preview-modal { background-color: #1f2937; }
.preview-header {
  display: flex; align-items: center; justify-content: space-between;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  border-bottom: 1px solid #e5e7eb;
}
:root.dark .preview-header { border-bottom-color: #374151; }
.preview-title {
  font-size: 0.875rem; color: #374151;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
:root.dark .preview-title { color: #d1d5db; }
.preview-body {
  display: flex; align-items: center; justify-content: center;
  padding: 1rem;
  background-color: #f9fafb;
  overflow: auto;
  cursor: zoom-out;
}
:root.dark .preview-body { background-color: #111827; }
.preview-body img {
  max-width: 100%;
  max-height: calc(85vh - 4rem);
  object-fit: contain;
  cursor: default;
}
</style>
