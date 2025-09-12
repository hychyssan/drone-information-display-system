<script setup lang="ts">
import * as echarts from 'echarts/core'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent, DataZoomComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { onMounted, onBeforeUnmount, ref, watch } from 'vue'
import { useTelemetryStore } from '@/stores/telemetry'

echarts.use([LineChart, GridComponent, TooltipComponent, LegendComponent, DataZoomComponent, CanvasRenderer])

const el = ref<HTMLDivElement | null>(null)
let chart: echarts.ECharts | null = null
const telemetry = useTelemetryStore()

function render() {
  if (!el.value) return
  if (!chart) chart = echarts.init(el.value)
  const frames = telemetry.frames
  const xs = frames.map(f => new Date(f.timestamp).toLocaleTimeString())
  const people = frames.map(f => f.peopleCount)
  const conf = frames.map(f => Number((f.confidence).toFixed(0)))

  chart.setOption({
    animation: false,
    grid: { left: 40, right: 16, top: 24, bottom: 40 },
    tooltip: { trigger: 'axis' },
    legend: { data: ['人数', '置信度%'] },
    xAxis: { type: 'category', data: xs },
    yAxis: [
      { type: 'value', name: '人数', minInterval: 1 },
      { type: 'value', name: '置信度%', min: 0, max: 100 }
    ],
    dataZoom: [{ type: 'inside' }, { type: 'slider' }],
    series: [
      { name: '人数', type: 'line', yAxisIndex: 0, smooth: true, showSymbol: false, data: people },
      { name: '置信度%', type: 'line', yAxisIndex: 1, smooth: true, showSymbol: false, data: conf }
    ],
  })
}

onMounted(() => {
  render()
  window.addEventListener('resize', render)
})
onBeforeUnmount(() => {
  if (chart) { chart.dispose(); chart = null }
  window.removeEventListener('resize', render)
})

watch(() => telemetry.frames.length, () => render())
</script>

<template>
  <div class="rounded-lg border border-gray-200 bg-white p-2 dark:border-gray-800 dark:bg-gray-900">
    <div ref="el" class="h-64 w-full"></div>
  </div>
</template>

<style scoped>
</style>

