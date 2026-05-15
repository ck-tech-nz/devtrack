<template>
  <div class="step-describe">
    <div class="chips">
      <button v-for="chip in chips" :key="chip.label" class="chip" type="button" @click="fillChip(chip.value)">
        {{ chip.label }}
      </button>
    </div>

    <div class="input-wrap">
      <div class="input-header">
        <USelect
          v-model="projectId"
          :items="projectOptions"
          value-key="value"
          size="sm"
          placeholder="选择项目"
          class="project-select"
          :ui="{ base: 'min-w-44' }"
        />
      </div>

      <UTextarea
        v-model="description"
        :rows="3"
        placeholder="描述你发现的问题：在哪个页面、做了什么操作、出现了什么现象？也可以粘贴截图 (Ctrl+V) 或拖拽文件…"
        autoresize
      />

      <div class="toolbar">
        <UButton size="xs" variant="ghost" color="neutral" icon="i-heroicons-plus" />
        <UButton size="xs" variant="ghost" color="neutral" icon="i-heroicons-photo" />
        <span class="toolbar-hint">拖拽 · Ctrl+V 粘贴 · Enter 分析</span>
        <div class="toolbar-spacer" />
        <USelect
          v-model="modelLabel"
          :items="modelOptions"
          size="xs"
          class="model-select"
          disabled
        />
        <UButton
          size="sm"
          icon="i-heroicons-magnifying-glass"
          :disabled="!canAnalyze"
          @click="onAnalyze"
        >
          AI 分析
        </UButton>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
type Project = { id: string; name: string }

const props = defineProps<{
  projects: Project[]
  defaultProjectId: string | null
}>()

const emit = defineEmits<{
  analyze: [payload: { description: string; project: string }]
}>()

const description = ref('')
const projectId = ref<string>(props.defaultProjectId ?? '')
const modelLabel = ref('✦ GPT-4o')

const projectOptions = computed(() =>
  props.projects.map(p => ({ label: p.name, value: String(p.id) })),
)

const modelOptions = ['✦ GPT-4o', '◆ Claude 3.5', '◉ Gemini 2.0']

const chips = [
  { label: '🖱 按钮无响应', value: '点击提交按钮后页面没有任何反应，按钮无响应' },
  { label: '⬜ 页面白屏', value: '页面加载后出现白屏，控制台报错 Cannot read properties of undefined' },
  { label: '💾 数据未保存', value: '表单提交后数据没有保存，刷新后内容消失' },
  { label: '🔗 跳转异常', value: '通知中心点击待审批事项后跳转到错误页面' },
  { label: '🖼 上传异常', value: '上传图片后显示上传成功但图片列表中看不到' },
]

const canAnalyze = computed(() => description.value.trim().length >= 5 && !!projectId.value)

function fillChip(text: string) {
  description.value = text
}

function onAnalyze() {
  if (!canAnalyze.value) return
  emit('analyze', { description: description.value.trim(), project: projectId.value })
}

watch(() => props.defaultProjectId, (v) => {
  if (v && !projectId.value) projectId.value = v
})
</script>

<style scoped>
.step-describe { display: flex; flex-direction: column; gap: 1rem; }
.chips { display: flex; flex-wrap: wrap; gap: 0.5rem; }
.chip {
  padding: 0.375rem 0.875rem;
  border-radius: 9999px;
  background-color: #f3f4f6;
  font-size: 0.8125rem;
  color: #374151;
  border: 1px solid transparent;
  cursor: pointer;
  transition: background-color 0.15s;
}
.chip:hover { background-color: #e5e7eb; }
:root.dark .chip { background-color: #1f2937; color: #d1d5db; }
:root.dark .chip:hover { background-color: #374151; }

.input-wrap {
  display: flex; flex-direction: column; gap: 0.75rem;
  border: 1px solid #e5e7eb;
  border-radius: 0.875rem;
  padding: 0.875rem;
  background-color: #ffffff;
}
:root.dark .input-wrap { border-color: #374151; background-color: #111827; }

.input-header { display: flex; gap: 0.5rem; }
.project-select :deep(button) { font-size: 0.8125rem; }

.toolbar { display: flex; align-items: center; gap: 0.5rem; }
.toolbar-hint { font-size: 0.75rem; color: #9ca3af; }
.toolbar-spacer { flex: 1; }
.model-select :deep(button) { min-width: 8rem; font-size: 0.75rem; }
</style>
