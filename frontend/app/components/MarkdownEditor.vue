<template>
  <div
    class="markdown-editor border rounded-xl overflow-hidden"
    :class="[
      isDragging ? 'border-primary-500 bg-primary-50 dark:bg-primary-950' : 'border-gray-200 dark:border-gray-700',
    ]"
    @dragover.prevent="isDragging = true"
    @dragleave.prevent="isDragging = false"
    @drop.prevent="handleDrop"
  >
    <!-- Tab bar -->
    <div class="flex border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800">
      <button
        class="px-4 py-2 text-sm font-medium transition-colors"
        :class="mode === 'edit'
          ? 'text-gray-900 dark:text-gray-100 border-b-2 border-primary-500'
          : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'"
        @click="mode = 'edit'"
      >
        编辑
      </button>
      <button
        class="px-4 py-2 text-sm font-medium transition-colors"
        :class="mode === 'preview'
          ? 'text-gray-900 dark:text-gray-100 border-b-2 border-primary-500'
          : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'"
        @click="mode = 'preview'"
      >
        预览
      </button>
    </div>

    <!-- Edit mode -->
    <div v-show="mode === 'edit'">
      <textarea
        ref="textareaRef"
        :value="modelValue"
        :placeholder="placeholder"
        class="w-full min-h-[260px] p-4 text-sm bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 resize-y outline-none"
        @input="$emit('update:modelValue', ($event.target as HTMLTextAreaElement).value)"
        @paste="handlePaste"
      />
      <!-- Toolbar -->
      <div class="flex items-center gap-2 px-4 py-2 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800">
        <button
          class="flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 transition-colors"
          @click="triggerFileInput"
        >
          <UIcon name="i-heroicons-photo" class="w-4 h-4" />
          <span>添加图片</span>
        </button>
        <span class="text-xs text-gray-400 dark:text-gray-500">粘贴、拖放或点击上传图片</span>
        <input
          ref="fileInputRef"
          type="file"
          accept="image/png,image/jpeg,image/gif,image/webp"
          multiple
          class="hidden"
          @change="handleFileSelect"
        />
      </div>
    </div>

    <!-- Preview mode -->
    <div
      v-show="mode === 'preview'"
      class="markdown-body min-h-[260px] p-4 bg-white dark:bg-gray-900 text-sm"
      v-html="renderedHtml"
    />
  </div>
</template>

<script setup lang="ts">
import MarkdownIt from 'markdown-it'

const props = defineProps<{
  modelValue: string
  placeholder?: string
  defaultMode?: 'edit' | 'preview'
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

const { api } = useApi()
const toast = useToast()

const mode = ref<'edit' | 'preview'>(props.defaultMode || 'edit')
const isDragging = ref(false)
const textareaRef = ref<HTMLTextAreaElement | null>(null)
const fileInputRef = ref<HTMLInputElement | null>(null)

const md = new MarkdownIt({ html: false, linkify: true })

const renderedHtml = computed(() => {
  if (!props.modelValue) return '<p class="text-gray-400 dark:text-gray-500">无内容</p>'
  return md.render(props.modelValue)
})

const ALLOWED_TYPES = new Set(['image/png', 'image/jpeg', 'image/gif', 'image/webp'])
const MAX_SIZE = 5 * 1024 * 1024

function triggerFileInput() {
  fileInputRef.value?.click()
}

function handleFileSelect(e: Event) {
  const input = e.target as HTMLInputElement
  if (input.files) {
    uploadFiles(Array.from(input.files))
    input.value = ''
  }
}

function handleDrop(e: DragEvent) {
  isDragging.value = false
  if (e.dataTransfer?.files) {
    uploadFiles(Array.from(e.dataTransfer.files))
  }
}

function handlePaste(e: ClipboardEvent) {
  const items = e.clipboardData?.items
  if (!items) return
  const images: File[] = []
  for (const item of items) {
    if (item.type.startsWith('image/')) {
      const file = item.getAsFile()
      if (file) images.push(file)
    }
  }
  if (images.length) {
    e.preventDefault()
    uploadFiles(images)
  }
}

function insertAtCursor(text: string): { start: number; end: number } {
  const ta = textareaRef.value
  if (!ta) {
    const current = props.modelValue || ''
    emit('update:modelValue', current + text)
    return { start: current.length, end: current.length + text.length }
  }
  const start = ta.selectionStart
  const before = props.modelValue.slice(0, start)
  const after = props.modelValue.slice(ta.selectionEnd)
  emit('update:modelValue', before + text + after)
  const newPos = start + text.length
  nextTick(() => {
    ta.selectionStart = ta.selectionEnd = newPos
    ta.focus()
  })
  return { start, end: start + text.length }
}

function replacePlaceholder(placeholder: string, replacement: string) {
  const current = props.modelValue || ''
  const idx = current.indexOf(placeholder)
  if (idx >= 0) {
    emit('update:modelValue', current.slice(0, idx) + replacement + current.slice(idx + placeholder.length))
  }
}

async function uploadFiles(files: File[]) {
  for (const file of files) {
    if (!ALLOWED_TYPES.has(file.type)) {
      toast.add({ title: `不支持的文件类型: ${file.type}`, color: 'error' })
      continue
    }
    if (file.size > MAX_SIZE) {
      toast.add({ title: `文件 ${file.name} 超过 5MB 限制`, color: 'error' })
      continue
    }

    const placeholder = `![上传中 ${file.name}...]()`
    insertAtCursor('\n' + placeholder + '\n')

    try {
      const formData = new FormData()
      formData.append('file', file)
      const res = await api<{ url: string; filename: string }>('/api/tools/upload/image/', {
        method: 'POST',
        body: formData,
      })
      replacePlaceholder(placeholder, `![${res.filename}](${res.url})`)
    } catch {
      replacePlaceholder(placeholder, `![上传失败 ${file.name}]()`)
      toast.add({ title: `上传失败: ${file.name}`, color: 'error' })
    }
  }
}
</script>

<style>
/* Markdown preview styles */
.markdown-body h1 { font-size: 1.5em; font-weight: 700; margin: 0.67em 0; border-bottom: 1px solid #e5e7eb; padding-bottom: 0.3em; }
.markdown-body h2 { font-size: 1.25em; font-weight: 600; margin: 0.83em 0; border-bottom: 1px solid #e5e7eb; padding-bottom: 0.3em; }
.markdown-body h3 { font-size: 1.1em; font-weight: 600; margin: 1em 0; }
.markdown-body p { margin: 0.5em 0; line-height: 1.6; }
.markdown-body ul, .markdown-body ol { margin: 0.5em 0; padding-left: 2em; }
.markdown-body li { margin: 0.25em 0; }
.markdown-body code { background: #f3f4f6; padding: 0.2em 0.4em; border-radius: 3px; font-size: 0.875em; }
.markdown-body pre { background: #f3f4f6; padding: 1em; border-radius: 6px; overflow-x: auto; margin: 0.5em 0; }
.markdown-body pre code { background: none; padding: 0; }
.markdown-body blockquote { border-left: 4px solid #d1d5db; padding-left: 1em; color: #6b7280; margin: 0.5em 0; }
.markdown-body img { max-width: 100%; border-radius: 6px; margin: 0.5em 0; }
.markdown-body a { color: #2563eb; text-decoration: none; }
.markdown-body a:hover { text-decoration: underline; }
.markdown-body hr { border: none; border-top: 1px solid #e5e7eb; margin: 1em 0; }
.markdown-body table { border-collapse: collapse; width: 100%; margin: 0.5em 0; }
.markdown-body th, .markdown-body td { border: 1px solid #d1d5db; padding: 0.5em 0.75em; text-align: left; }
.markdown-body th { background: #f9fafb; font-weight: 600; }

/* Dark mode */
:root.dark .markdown-body code { background: #1f2937; }
:root.dark .markdown-body pre { background: #1f2937; }
:root.dark .markdown-body blockquote { border-left-color: #4b5563; color: #9ca3af; }
:root.dark .markdown-body h1, :root.dark .markdown-body h2 { border-bottom-color: #374151; }
:root.dark .markdown-body a { color: #60a5fa; }
:root.dark .markdown-body hr { border-top-color: #374151; }
:root.dark .markdown-body th, :root.dark .markdown-body td { border-color: #4b5563; }
:root.dark .markdown-body th { background: #1f2937; }
</style>
