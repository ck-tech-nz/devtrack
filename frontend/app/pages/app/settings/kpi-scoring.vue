<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <h1 class="text-2xl font-semibold text-gray-900 dark:text-gray-100">KPI 评分规则</h1>
      <UButton
        size="sm"
        icon="i-heroicons-check"
        :loading="saving"
        @click="handleSave"
      >
        保存
      </UButton>
    </div>

    <div v-if="loading" class="text-center py-20 text-sm text-gray-400">加载中...</div>

    <template v-else-if="config">
      <!-- 综合分维度权重 -->
      <ScoringCard title="综合分维度权重" description="5 个维度在综合分中的权重，总和应为 1.0">
        <div class="grid grid-cols-2 lg:grid-cols-5 gap-4">
          <ScoringField
            v-for="(val, key) in config.dimension_weights"
            :key="key"
            :label="dimLabel(key as string)"
            :model-value="val as number"
            @update:model-value="config.dimension_weights[key] = $event"
            :step="0.05"
            :min="0"
            :max="1"
          />
        </div>
        <WeightSum :weights="config.dimension_weights" />
      </ScoringCard>

      <!-- 效率 -->
      <ScoringCard title="效率评分公式" description="效率维度各子指标权重">
        <div class="grid grid-cols-2 lg:grid-cols-3 gap-4">
          <ScoringField
            v-for="(val, key) in config.efficiency_formula"
            :key="key"
            :label="subLabel('efficiency', key as string)"
            :model-value="val as number"
            @update:model-value="config.efficiency_formula[key] = $event"
            :step="0.05"
            :min="0"
            :max="1"
          />
        </div>
        <WeightSum :weights="config.efficiency_formula" />
      </ScoringCard>

      <!-- 产出 -->
      <ScoringCard title="产出评分公式" description="产出维度各子指标权重">
        <div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <ScoringField
            v-for="(val, key) in config.output_formula"
            :key="key"
            :label="subLabel('output', key as string)"
            :model-value="val as number"
            @update:model-value="config.output_formula[key] = $event"
            :step="0.05"
            :min="0"
            :max="1"
          />
        </div>
        <WeightSum :weights="config.output_formula" />
      </ScoringCard>

      <!-- 质量 -->
      <ScoringCard title="质量评分公式" description="质量维度各子指标权重">
        <div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <ScoringField
            v-for="(val, key) in config.quality_formula"
            :key="key"
            :label="subLabel('quality', key as string)"
            :model-value="val as number"
            @update:model-value="config.quality_formula[key] = $event"
            :step="0.05"
            :min="0"
            :max="1"
          />
        </div>
        <WeightSum :weights="config.quality_formula" />
      </ScoringCard>

      <!-- 能力 -->
      <ScoringCard title="能力评分公式" description="能力维度各子指标权重">
        <div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <ScoringField
            v-for="(val, key) in config.capability_formula"
            :key="key"
            :label="subLabel('capability', key as string)"
            :model-value="val as number"
            @update:model-value="config.capability_formula[key] = $event"
            :step="0.05"
            :min="0"
            :max="1"
          />
        </div>
        <WeightSum :weights="config.capability_formula" />
      </ScoringCard>

      <!-- 饱和天花板值 -->
      <ScoringCard title="饱和天花板值" description="各指标达到满分 100 的阈值">
        <div class="grid grid-cols-2 lg:grid-cols-3 gap-4">
          <ScoringField
            v-for="(val, key) in config.ceilings"
            :key="key"
            :label="ceilingLabel(key as string)"
            :model-value="val as number"
            @update:model-value="config.ceilings[key] = $event"
            :step="1"
            :min="1"
            :max="1000"
          />
        </div>
      </ScoringCard>
    </template>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ layout: 'default' })

const { api } = useApi()
const toast = useToast()

const loading = ref(true)
const saving = ref(false)
const config = ref<any>(null)

const DIM_LABELS: Record<string, string> = {
  efficiency: '效率',
  output: '产出',
  quality: '质量',
  capability: '能力',
  growth: '成长',
}

const SUB_LABELS: Record<string, Record<string, string>> = {
  efficiency: {
    daily_resolved: '日均解决',
    speed: '解决速度',
    p0p1_speed: 'P0/P1 速度',
  },
  output: {
    weighted_issue_value: '加权价值',
    resolved_count: '解决数量',
    commit_volume: '提交量',
    repo_breadth: '仓库广度',
  },
  quality: {
    inv_bug_rate: '反向 Bug 率',
    inv_churn_rate: '反向 Churn 率',
    commit_size: '提交大小',
    conventional_ratio: '规范提交率',
  },
  capability: {
    file_type_breadth: '文件类型广度',
    repo_coverage: '仓库覆盖',
    p0_handling_ratio: 'P0 处理比',
    helper_participation: '协助参与',
  },
}

const CEILING_LABELS: Record<string, string> = {
  daily_resolved: '日均解决 (个)',
  avg_hours: '平均解决时间 (小时)',
  p0p1_hours: 'P0/P1 解决时间 (小时)',
  weighted_value: '加权价值上限',
  resolved_count: '期间解决数 (个)',
  commit_volume: '提交量 (个)',
  repo_breadth: '仓库覆盖 (个)',
  file_type: '文件类型 (种)',
  helper_count: '协助数量 (个)',
}

function dimLabel(key: string) { return DIM_LABELS[key] || key }
function subLabel(dim: string, key: string) { return SUB_LABELS[dim]?.[key] || key }
function ceilingLabel(key: string) { return CEILING_LABELS[key] || key }

async function fetchConfig() {
  loading.value = true
  try {
    config.value = await api('/api/kpi/scoring-config/')
  } catch { /* empty */ } finally {
    loading.value = false
  }
}

async function handleSave() {
  saving.value = true
  try {
    const { updated_at, ...payload } = config.value
    config.value = await api('/api/kpi/scoring-config/', { method: 'PUT', body: payload })
    toast.add({ title: '评分规则已保存', color: 'success' })
  } catch (e: any) {
    toast.add({ title: '保存失败', description: e?.data?.detail || '请稍后重试', color: 'error' })
  } finally {
    saving.value = false
  }
}

onMounted(fetchConfig)
</script>
