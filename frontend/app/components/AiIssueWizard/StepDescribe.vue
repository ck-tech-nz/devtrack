<template>
  <div class="step-describe">
    <div class="input-wrap">
      <UTextarea
        v-model="description"
        :rows="3"
        placeholder="描述你发现的问题：在哪个页面、做了什么操作、出现了什么现象？"
        autoresize
        variant="none"
      />

      <div class="toolbar">
        <UButton size="xs" variant="ghost" color="neutral" icon="i-heroicons-plus" />
        <UButton size="xs" variant="ghost" color="neutral" icon="i-heroicons-photo" />
        <USelect
          v-model="projectId"
          :items="projectOptions"
          value-key="value"
          size="xs"
          icon="i-heroicons-folder"
          placeholder="选择项目"
          class="project-chip"
        />
        <div class="toolbar-spacer" />
        <UButton
          icon="i-heroicons-arrow-up"
          color="primary"
          size="sm"
          :disabled="!canAnalyze"
          class="send-btn"
          title="AI 分析"
          @click="onAnalyze"
        />
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

const projectOptions = computed(() =>
  props.projects.map(p => ({ label: p.name, value: String(p.id) })),
)

const canAnalyze = computed(() => description.value.trim().length >= 5 && !!projectId.value)

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

.input-wrap {
  display: flex; flex-direction: column;
  border: 1px solid #e5e7eb;
  border-radius: 1rem;
  padding: 0.75rem 1rem;
  background-color: #ffffff;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}
:root.dark .input-wrap { border-color: #374151; background-color: #1f2937; }

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
</style>
