<template>
  <div ref="chartRef" class="w-full" :style="{ height: height + 'px' }" />
</template>

<script setup lang="ts">
import * as echarts from 'echarts/core'
import { LineChart as ELineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

echarts.use([ELineChart, GridComponent, TooltipComponent, LegendComponent, CanvasRenderer])

const props = withDefaults(defineProps<{
  xData: string[]
  series: { name: string; data: number[] }[]
  height?: number
}>(), { height: 300 })

const chartRef = ref<HTMLElement>()
let chart: echarts.ECharts | null = null

const colors = ['#8b5cf6', '#a78bfa', '#c4b5fd']

const colorMode = useColorMode()
const isDark = computed(() => colorMode.value === 'dark')

onMounted(() => {
  if (!chartRef.value) return
  chart = echarts.init(chartRef.value)
  renderChart()
})

watch(() => [props.xData, props.series], renderChart, { deep: true })
watch(isDark, () => renderChart())

function renderChart() {
  if (!chart) return
  const dark = isDark.value
  chart.setOption({
    tooltip: {
      trigger: 'axis',
      backgroundColor: dark ? '#1f2937' : '#fff',
      borderColor: dark ? '#374151' : '#e5e7eb',
      textStyle: { color: dark ? '#e5e7eb' : '#374151', fontSize: 12 },
    },
    grid: { left: 40, right: 16, top: 24, bottom: 28 },
    xAxis: { type: 'category', data: props.xData, axisLine: { show: false }, axisTick: { show: false }, axisLabel: { color: dark ? '#6b7280' : '#9ca3af', fontSize: 11 } },
    yAxis: { type: 'value', splitLine: { lineStyle: { color: dark ? '#374151' : '#f3f4f6' } }, axisLabel: { color: dark ? '#6b7280' : '#9ca3af', fontSize: 11 } },
    series: props.series.map((s, i) => ({
      name: s.name,
      type: 'line',
      data: s.data,
      smooth: true,
      symbol: 'none',
      lineStyle: { width: 2, color: colors[i % colors.length] },
      areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
        { offset: 0, color: colors[i % colors.length] + '20' },
        { offset: 1, color: colors[i % colors.length] + '02' },
      ]) },
    })),
  })
}

onUnmounted(() => {
  observer?.disconnect()
  chart?.dispose()
})

let observer: ResizeObserver | null = null
onMounted(() => {
  if (chartRef.value) {
    observer = new ResizeObserver(() => { chart?.resize() })
    observer.observe(chartRef.value)
  }
})
</script>
