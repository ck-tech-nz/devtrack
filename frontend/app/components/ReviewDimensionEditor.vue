<template>
  <div class="space-y-2">
    <div
      v-for="(d, i) in model"
      :key="d.key"
      class="flex items-center gap-2"
    >
      <UInput v-model="d.label" size="xs" variant="outline" placeholder="维度名称" class="flex-1" />
      <UInput
        v-model.number="d.weight"
        size="xs" variant="outline" type="number" :step="0.05" :min="0" :max="1"
        class="w-20"
      />
      <UButton size="xs" variant="ghost" color="error" icon="i-heroicons-trash" @click="remove(i)" />
    </div>

    <div class="flex items-center gap-2 pt-1">
      <UButton size="xs" variant="outline" color="neutral" icon="i-heroicons-plus" @click="add">
        加维度
      </UButton>
      <UButton
        v-if="poolUnused.length"
        size="xs" variant="ghost" color="neutral" icon="i-heroicons-arrow-down-on-square"
        @click="addFromPool"
      >
        从维度库添加
      </UButton>
      <span class="text-xs text-gray-400">权重和：{{ weightSum.toFixed(2) }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
interface Dim { key: string; label: string; weight: number }

const model = defineModel<Dim[]>({ default: () => [] })
const props = defineProps<{ pool?: Dim[] }>()

const weightSum = computed(() => model.value.reduce((s, d) => s + (Number(d.weight) || 0), 0))
const poolUnused = computed(() =>
  (props.pool || []).filter(p => !model.value.some(d => d.key === p.key)),
)

function add() {
  model.value.push({ key: crypto.randomUUID(), label: '', weight: 0.1 })
}
function addFromPool() {
  const next = poolUnused.value[0]
  if (next) model.value.push({ ...next })
}
function remove(i: number) {
  model.value.splice(i, 1)
}
</script>
