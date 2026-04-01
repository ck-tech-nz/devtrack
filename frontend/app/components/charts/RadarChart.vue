<template>
  <div ref="chartRef" class="w-full" :style="{ height: height + 'px' }" />
</template>

<script setup lang="ts">
import * as echarts from 'echarts/core'
import { RadarChart as ERadarChart } from 'echarts/charts'
import { TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

echarts.use([ERadarChart, TooltipComponent, CanvasRenderer])

const props = withDefaults(defineProps<{
  indicators: { name: string; max: number }[]
  values: number[]
  height?: number
}>(), { height: 280 })

const chartRef = ref<HTMLElement>()
let chart: echarts.ECharts | null = null

const colorMode = useColorMode()
const isDark = computed(() => colorMode.value === 'dark')

onMounted(() => {
  if (!chartRef.value) return
  chart = echarts.init(chartRef.value)
  renderChart()
})

watch(() => [props.indicators, props.values], renderChart, { deep: true })
watch(isDark, () => renderChart())

function renderChart() {
  if (!chart) return
  const dark = isDark.value
  chart.setOption({
    tooltip: {
      backgroundColor: dark ? '#1f2937' : '#fff',
      borderColor: dark ? '#374151' : '#e5e7eb',
      textStyle: { color: dark ? '#e5e7eb' : '#374151', fontSize: 12 },
    },
    radar: {
      indicator: props.indicators,
      shape: 'polygon',
      splitNumber: 4,
      axisName: {
        color: dark ? '#9ca3af' : '#6b7280',
        fontSize: 12,
        fontWeight: 600,
      },
      splitArea: {
        areaStyle: {
          color: dark
            ? ['rgba(55,65,81,0.3)', 'rgba(55,65,81,0.15)']
            : ['rgba(241,245,249,0.8)', 'rgba(248,250,252,0.5)'],
        },
      },
      axisLine: { lineStyle: { color: dark ? '#374151' : '#e2e8f0' } },
      splitLine: { lineStyle: { color: dark ? '#374151' : '#e2e8f0' } },
    },
    series: [{
      type: 'radar',
      data: [{
        value: props.values,
        areaStyle: { color: 'rgba(99,102,241,0.15)' },
        lineStyle: { color: '#6366f1', width: 2 },
        itemStyle: { color: '#6366f1' },
      }],
    }],
  })
}

let observer: ResizeObserver | null = null
onMounted(() => {
  if (chartRef.value) {
    observer = new ResizeObserver(() => { chart?.resize() })
    observer.observe(chartRef.value)
  }
})
onUnmounted(() => { observer?.disconnect(); chart?.dispose() })
</script>
