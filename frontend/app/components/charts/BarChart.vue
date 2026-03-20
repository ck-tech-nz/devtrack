<template>
  <div ref="chartRef" class="w-full" :style="{ height: height + 'px' }" />
</template>

<script setup lang="ts">
import * as echarts from 'echarts/core'
import { BarChart as EBarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

echarts.use([EBarChart, GridComponent, TooltipComponent, CanvasRenderer])

const props = withDefaults(defineProps<{
  xData: string[]
  series: { name: string; data: number[] }[]
  height?: number
  horizontal?: boolean
}>(), { height: 300, horizontal: false })

const chartRef = ref<HTMLElement>()
let chart: echarts.ECharts | null = null
const colors = ['#8b5cf6', '#a78bfa', '#c4b5fd', '#ddd6fe']

onMounted(() => {
  if (!chartRef.value) return
  chart = echarts.init(chartRef.value)
  renderChart()
})

watch(() => [props.xData, props.series, props.horizontal], renderChart, { deep: true })

function renderChart() {
  if (!chart) return
  const categoryAxis = { type: 'category' as const, data: props.xData, axisLine: { show: false }, axisTick: { show: false }, axisLabel: { color: '#9ca3af', fontSize: 11 } }
  const valueAxis = { type: 'value' as const, splitLine: { lineStyle: { color: '#f3f4f6' } }, axisLabel: { color: '#9ca3af', fontSize: 11 } }

  chart.setOption({
    tooltip: { trigger: 'axis', backgroundColor: '#fff', borderColor: '#e5e7eb', textStyle: { color: '#374151', fontSize: 12 } },
    grid: { left: props.horizontal ? 80 : 40, right: 16, top: 16, bottom: 28 },
    xAxis: props.horizontal ? valueAxis : categoryAxis,
    yAxis: props.horizontal ? categoryAxis : valueAxis,
    series: props.series.map((s, i) => ({
      name: s.name,
      type: 'bar',
      data: s.data,
      barWidth: props.horizontal ? 16 : undefined,
      barMaxWidth: 32,
      itemStyle: { color: colors[i % colors.length], borderRadius: props.horizontal ? [0, 4, 4, 0] : [4, 4, 0, 0] },
    })),
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
