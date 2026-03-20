<template>
  <div ref="chartRef" class="w-full" :style="{ height: height + 'px' }" />
</template>

<script setup lang="ts">
import * as echarts from 'echarts/core'
import { PieChart as EPieChart } from 'echarts/charts'
import { TooltipComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

echarts.use([EPieChart, TooltipComponent, LegendComponent, CanvasRenderer])

const props = withDefaults(defineProps<{
  data: { name: string; value: number }[]
  height?: number
}>(), { height: 300 })

const chartRef = ref<HTMLElement>()
let chart: echarts.ECharts | null = null
const colors = ['#8b5cf6', '#a78bfa', '#c4b5fd', '#ddd6fe', '#ede9fe']

onMounted(() => {
  if (!chartRef.value) return
  chart = echarts.init(chartRef.value)
  renderChart()
})

watch(() => props.data, renderChart, { deep: true })

function renderChart() {
  if (!chart) return
  chart.setOption({
    tooltip: { trigger: 'item', backgroundColor: '#fff', borderColor: '#e5e7eb', textStyle: { color: '#374151', fontSize: 12 } },
    legend: { bottom: 0, itemWidth: 8, itemHeight: 8, textStyle: { color: '#6b7280', fontSize: 11 } },
    color: colors,
    series: [{
      type: 'pie',
      radius: ['45%', '70%'],
      center: ['50%', '45%'],
      avoidLabelOverlap: true,
      label: { show: false },
      emphasis: { label: { show: true, fontSize: 13, fontWeight: 600 } },
      data: props.data,
      itemStyle: { borderRadius: 4, borderColor: '#fff', borderWidth: 2 },
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
