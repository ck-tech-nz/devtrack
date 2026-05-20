<template>
  <div class="step-describe">
    <!-- 对话流: 用户发出的描述 + AI 思考过程, 渲染在 composer 之上 -->
    <transition name="thread-fade">
      <div v-if="showThread" class="thread" aria-live="polite">
        <!-- 用户消息: 右对齐气泡 + 附件预览 -->
        <div class="msg msg--user">
          <div v-if="sentAttachments.length" class="msg-attach-row">
            <button
              v-for="att in sentAttachments"
              :key="att.id"
              type="button"
              class="msg-attach"
              :class="{ 'msg-attach--image': isImage(att.file_name) }"
              :title="att.file_name"
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

        <!-- AI 消息: 左对齐, 品牌标识 + 流式步骤 + 思考光标 -->
        <div class="msg msg--ai">
          <div class="msg-brand">
            <span class="msg-brand-mark">
              <UIcon name="i-heroicons-sparkles" class="w-3 h-3" />
            </span>
            <span class="msg-brand-name">DevTrakr</span>
            <span v-if="!errorMessage" class="msg-brand-status">
              <span class="brand-pulse" /> 正在思考
            </span>
          </div>

          <div class="msg-thinking">
            <div
              v-for="s in steps"
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
            <div v-if="!steps.length && !errorMessage" class="think-line think-line--running">
              <span class="think-dot" />
              <span class="think-label">连接 AI 服务…</span>
            </div>
          </div>

          <div v-if="errorMessage" class="msg-error">
            <UIcon name="i-heroicons-exclamation-triangle" class="w-3.5 h-3.5" />
            <span>{{ errorMessage }}</span>
          </div>

          <div v-if="errorMessage" class="msg-actions">
            <button type="button" class="msg-action msg-action--primary" @click="emit('retry')">重试</button>
            <button type="button" class="msg-action" @click="emit('cancel')">重新描述</button>
          </div>
        </div>
      </div>
    </transition>

    <div class="input-wrap" :class="{ 'input-wrap--busy': analyzing }">
      <!-- 附件预览行: composer 编辑态时显示, analyzing 时附件已上移至 thread -->
      <div v-if="attachments.length && !analyzing" class="attach-row">
        <div v-for="att in attachments" :key="att.id" class="attach-chip" :class="{ 'attach-chip--image': isImage(att.file_name) }">
          <button
            v-if="isImage(att.file_name)"
            type="button"
            class="attach-thumb"
            :title="`预览 ${att.file_name}`"
            @click="openPreview(att)"
          >
            <img :src="att.file_url" :alt="att.file_name" />
          </button>
          <UIcon v-else name="i-heroicons-document" class="w-3.5 h-3.5 attach-icon" />
          <span v-if="!isImage(att.file_name)" class="attach-name">{{ att.file_name }}</span>
          <button class="attach-remove" :title="`移除 ${att.file_name}`" @click="removeAttachment(att.id)">
            <UIcon name="i-heroicons-x-mark" class="w-3 h-3" />
          </button>
        </div>
      </div>

      <!-- 图片预览弹窗 -->
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

      <UTextarea
        v-model="description"
        :rows="3"
        :placeholder="analyzing ? 'AI 正在生成草稿，可点击 ■ 取消…' : '描述问题：哪个页面/角色，做了什么，看到什么。可以贴截图——AI 会读取截图内容。'"
        autoresize
        variant="none"
        :disabled="analyzing"
        @paste="onPaste"
        @drop.prevent="onDrop"
        @dragover.prevent
        @keydown="onKeydown"
      />

      <!-- 隐藏文件输入 -->
      <input
        ref="fileInputRef"
        type="file"
        multiple
        accept="image/*,.pdf,.txt,.md,.log,.zip"
        style="display:none"
        @change="onFileSelect"
      />
      <input
        ref="imgInputRef"
        type="file"
        multiple
        accept="image/*"
        style="display:none"
        @change="onFileSelect"
      />

      <div class="toolbar">
        <UButton
          size="xs"
          variant="ghost"
          color="neutral"
          icon="i-heroicons-plus"
          title="添加附件"
          :disabled="analyzing"
          @click="fileInputRef?.click()"
        />
        <UButton
          size="xs"
          variant="ghost"
          color="neutral"
          icon="i-heroicons-photo"
          title="添加图片"
          :disabled="analyzing"
          @click="imgInputRef?.click()"
        />
        <USelect
          v-model="projectId"
          :items="projectOptions"
          value-key="value"
          size="xs"
          icon="i-heroicons-folder"
          placeholder="选择项目"
          class="project-chip"
          :disabled="analyzing"
        />
        <div class="toolbar-spacer" />
        <span v-if="!analyzing && hintMessage" class="send-hint">{{ hintMessage }}</span>
        <UButton
          v-if="!analyzing"
          icon="i-heroicons-arrow-up"
          color="primary"
          size="sm"
          :disabled="!canAnalyze"
          class="send-btn"
          :title="hintMessage || 'AI 分析'"
          @click="onAnalyze"
        />
        <button
          v-else
          type="button"
          class="stop-btn"
          title="取消"
          @click="emit('cancel')"
        >
          <span class="stop-square" aria-hidden="true" />
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
type Project = { id: string; name: string }
type AttachmentRef = { id: string; file_name: string; file_url: string }
type StepStatus = 'pending' | 'running' | 'done' | 'error'
type StepProgress = { step: 1 | 2 | 3; label: string; status: StepStatus }

const props = defineProps<{
  projects: Project[]
  defaultProjectId: string | null
  analyzing?: boolean
  steps?: StepProgress[]
  errorMessage?: string
}>()

const emit = defineEmits<{
  analyze: [payload: { description: string; project: string; attachment_ids: string[] }]
  cancel: []
  retry: []
}>()

const { api } = useApi()

const description = ref('')
const projectId = ref<string>(props.defaultProjectId ?? '')
const fileInputRef = ref<HTMLInputElement | null>(null)
const imgInputRef = ref<HTMLInputElement | null>(null)
const attachments = ref<AttachmentRef[]>([])
const previewOpen = ref(false)
const previewAttachment = ref<AttachmentRef | null>(null)

// analyzing 期间渲染的"已发送"快照 — composer 视觉清空, 用户仍能看到自己发了什么
const sentDescription = ref('')
const sentAttachments = ref<AttachmentRef[]>([])

const steps = computed<StepProgress[]>(() => props.steps || [])
const errorMessage = computed(() => props.errorMessage || '')
const showThread = computed(() => props.analyzing === true)

function openPreview(att: AttachmentRef) {
  previewAttachment.value = att
  previewOpen.value = true
}

const projectOptions = computed(() =>
  props.projects.map(p => ({ label: p.name, value: String(p.id) })),
)

const MIN_DESC_LEN = 5
const trimmedLen = computed(() => description.value.trim().length)
const canAnalyze = computed(() => trimmedLen.value >= MIN_DESC_LEN && !!projectId.value && !props.analyzing)

// 平台检测：Mac 显示 ⌘，其他平台显示 Ctrl
const isMac = computed(() => {
  if (typeof navigator === 'undefined') return false
  return /Mac|iPhone|iPad|iPod/.test(navigator.platform)
})
const sendShortcutHint = computed(() => `${isMac.value ? '⌘' : 'Ctrl'} + Enter 发送`)

const hintMessage = computed(() => {
  if (trimmedLen.value > 0 && trimmedLen.value < MIN_DESC_LEN) {
    return `至少 ${MIN_DESC_LEN} 个字（当前 ${trimmedLen.value}）`
  }
  if (trimmedLen.value >= MIN_DESC_LEN && !projectId.value) return '请选择项目'
  return sendShortcutHint.value
})

function isImage(name: string): boolean {
  return /\.(png|jpe?g|gif|webp|bmp|svg)$/i.test(name || '')
}

async function uploadFile(file: File) {
  const fd = new FormData()
  fd.append('file', file)
  try {
    const res = await api<{ url: string; filename: string; id: string }>('/api/tools/upload/image/', {
      method: 'POST',
      body: fd,
    })
    attachments.value.push({ id: res.id, file_name: res.filename, file_url: res.url })
  } catch (e) {
    console.error('upload failed', e)
  }
}

function onFileSelect(e: Event) {
  const input = e.target as HTMLInputElement
  const files = Array.from(input.files || [])
  for (const f of files) uploadFile(f)
  input.value = ''
}

function onPaste(e: ClipboardEvent) {
  const items = e.clipboardData?.items || []
  for (const item of items) {
    if (item.kind === 'file') {
      const file = item.getAsFile()
      if (file) uploadFile(file)
    }
  }
}

function onDrop(e: DragEvent) {
  const files = Array.from(e.dataTransfer?.files || [])
  for (const f of files) uploadFile(f)
}

function removeAttachment(id: string) {
  attachments.value = attachments.value.filter(a => a.id !== id)
}

function onAnalyze() {
  if (!canAnalyze.value) return
  // 快照"已发送"内容,让 composer 视觉清空,但用户依然能在 thread 里看到自己发了什么
  sentDescription.value = description.value.trim()
  sentAttachments.value = [...attachments.value]
  emit('analyze', {
    description: sentDescription.value,
    project: projectId.value,
    attachment_ids: sentAttachments.value.map(a => a.id),
  })
  description.value = ''
  attachments.value = []
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
    e.preventDefault()
    onAnalyze()
  }
}

watch(() => props.defaultProjectId, (v) => {
  if (v && !projectId.value) projectId.value = v
})

// 父级把 analyzing 重置回 false (取消 / 出错时点了"重新描述") → 把快照还原到 composer 让用户继续编辑
watch(() => props.analyzing, (now, prev) => {
  if (prev && !now && (sentDescription.value || sentAttachments.value.length)) {
    description.value = sentDescription.value
    attachments.value = [...sentAttachments.value]
    sentDescription.value = ''
    sentAttachments.value = []
  }
})
</script>

<style scoped>
.step-describe { display: flex; flex-direction: column; gap: 0.875rem; }

/* ===========================================================
   Conversation thread — 渲染在 composer 之上
   =========================================================== */
.thread {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  padding: 0.25rem 0.125rem 0;
}

.thread-fade-enter-active { transition: opacity 0.25s ease, transform 0.25s ease; }
.thread-fade-leave-active { transition: opacity 0.15s ease; }
.thread-fade-enter-from { opacity: 0; transform: translateY(4px); }
.thread-fade-leave-to { opacity: 0; }

/* ---------- 通用消息块 ---------- */
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
@keyframes msg-rise {
  from { opacity: 0; transform: translateY(6px); }
  to { opacity: 1; transform: translateY(0); }
}

/* ---------- 用户气泡 ---------- */
.msg-bubble {
  max-width: min(36rem, 90%);
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
  max-width: min(36rem, 90%);
}
.msg-attach {
  display: inline-flex; align-items: center; gap: 0.25rem;
  padding: 0;
  border: 0;
  border-radius: 0.5rem;
  background: transparent;
  cursor: pointer;
  overflow: hidden;
}
.msg-attach--image {
  width: 3.5rem;
  height: 3.5rem;
  border: 1px solid #e5e7eb;
  background-color: #ffffff;
}
:root.dark .msg-attach--image { border-color: #374151; background-color: #111827; }
.msg-attach--image img { width: 100%; height: 100%; object-fit: cover; display: block; }
.msg-attach:not(.msg-attach--image) {
  padding: 0.25rem 0.5rem;
  background-color: #f9fafb;
  border: 1px solid #e5e7eb;
  font-size: 0.75rem;
  color: #4b5563;
  cursor: default;
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

.think-label { font-feature-settings: "cv11", "cv05"; }

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

/* ===========================================================
   Composer
   =========================================================== */
.input-wrap {
  display: flex; flex-direction: column;
  border: 1px solid #e5e7eb;
  border-radius: 1rem;
  padding: 0.75rem 1rem;
  background-color: #ffffff;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
  transition: opacity 0.2s ease, border-color 0.2s ease;
}
:root.dark .input-wrap { border-color: #374151; background-color: #1f2937; }
.input-wrap--busy {
  opacity: 0.6;
}

.toolbar { display: flex; align-items: center; gap: 0.5rem; padding-top: 0.5rem; }
.toolbar-spacer { flex: 1; }
.project-chip :deep(button) {
  font-size: 0.75rem;
  background-color: #f9fafb;
  border-color: #e5e7eb;
}
:root.dark .project-chip :deep(button) {
  background-color: #111827;
  border-color: #374151;
}
.send-btn { border-radius: 9999px !important; }
.send-hint {
  font-size: 0.75rem;
  color: #9ca3af;
  margin-right: 0.25rem;
  user-select: none;
}
:root.dark .send-hint { color: #6b7280; }

/* Stop 按钮 — 黑底方形, 视觉对应 Manus 的取消态 */
.stop-btn {
  width: 1.875rem; height: 1.875rem;
  border-radius: 9999px;
  border: 0;
  background-color: #111827;
  color: #ffffff;
  display: inline-flex; align-items: center; justify-content: center;
  cursor: pointer;
  transition: background-color 0.15s, transform 0.15s;
  opacity: 1;
}
.stop-btn:hover { background-color: #000000; transform: scale(1.05); }
:root.dark .stop-btn { background-color: #f3f4f6; color: #111827; }
:root.dark .stop-btn:hover { background-color: #ffffff; }
.stop-square {
  width: 0.5625rem; height: 0.5625rem;
  background-color: currentColor;
  border-radius: 0.0625rem;
  display: block;
}

/* ---------- 附件 chip (composer 编辑态) ---------- */
.attach-row {
  display: flex; flex-wrap: wrap; gap: 0.375rem;
  padding-bottom: 0.5rem;
}
.attach-chip {
  display: inline-flex; align-items: center; gap: 0.375rem;
  padding: 0.25rem 0.5rem;
  border: 1px solid #e5e7eb;
  border-radius: 0.5rem;
  background-color: #f9fafb;
  font-size: 0.75rem;
  color: #4b5563;
  max-width: 16rem;
  position: relative;
}
:root.dark .attach-chip { background-color: #1f2937; border-color: #374151; color: #d1d5db; }

.attach-chip--image {
  padding: 0.125rem 0.25rem 0.125rem 0.125rem;
  gap: 0.25rem;
}

.attach-thumb {
  display: block;
  width: 2rem;
  height: 2rem;
  padding: 0;
  border: 0;
  border-radius: 0.375rem;
  overflow: hidden;
  flex-shrink: 0;
  cursor: zoom-in;
  background-color: #ffffff;
}
.attach-thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
:root.dark .attach-thumb { background-color: #111827; }

.attach-icon {
  color: #6b7280;
  flex-shrink: 0;
}
:root.dark .attach-icon { color: #9ca3af; }

.attach-name {
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  max-width: 12rem;
}

.attach-remove {
  display: flex; align-items: center; justify-content: center;
  width: 1rem; height: 1rem; border-radius: 9999px;
  background-color: transparent; border: 0; cursor: pointer;
  color: #9ca3af;
  flex-shrink: 0;
}
.attach-remove:hover { background-color: #e5e7eb; color: #374151; }
:root.dark .attach-remove:hover { background-color: #374151; color: #d1d5db; }

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
