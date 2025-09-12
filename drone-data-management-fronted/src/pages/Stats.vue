<script setup lang="ts">
import { ref, computed } from 'vue'
import { useTelemetryStore } from '@/stores/telemetry'
import RangeChart from '@/components/RangeChart.vue'

const telemetry = useTelemetryStore()
const now = Date.now()
const start = ref(now - 5 * 60 * 1000) // 默认过去5分钟
const end = ref(now)

const data = computed(() => telemetry.getFramesInRange(start.value, end.value))
const summary = computed(() => telemetry.summarize(data.value))

function setPreset(minutes: number) {
  end.value = Date.now()
  start.value = end.value - minutes * 60 * 1000
}
</script>

<template>
  <div class="mx-auto max-w-6xl p-4 space-y-4">
    <div class="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900">
      <div class="flex flex-wrap items-center gap-3 text-sm">
        <div>时间范围：</div>
        <input type="datetime-local" class="rounded border px-2 py-1 dark:bg-gray-800" :value="new Date(start).toISOString().slice(0,16)" @change="e => start = new Date((e.target as HTMLInputElement).value).getTime()" />
        <span>—</span>
        <input type="datetime-local" class="rounded border px-2 py-1 dark:bg-gray-800" :value="new Date(end).toISOString().slice(0,16)" @change="e => end = new Date((e.target as HTMLInputElement).value).getTime()" />
        <div class="ml-auto flex items-center gap-2">
          <button class="rounded bg-gray-100 px-2 py-1 dark:bg-gray-800" @click="setPreset(1)">最近1分钟</button>
          <button class="rounded bg-gray-100 px-2 py-1 dark:bg-gray-800" @click="setPreset(5)">最近5分钟</button>
          <button class="rounded bg-gray-100 px-2 py-1 dark:bg-gray-800" @click="setPreset(30)">最近30分钟</button>
        </div>
      </div>
    </div>

    <div class="grid gap-4 md:grid-cols-3">
      <div class="rounded-lg border border-gray-200 bg-white p-4 text-center dark:border-gray-800 dark:bg-gray-900">
        <div class="text-xs text-gray-500">样本数</div>
        <div class="text-2xl font-semibold">{{ summary.count }}</div>
      </div>
      <div class="rounded-lg border border-gray-200 bg-white p-4 text-center dark:border-gray-800 dark:bg-gray-900">
        <div class="text-xs text-gray-500">平均置信度</div>
        <div class="text-2xl font-semibold">{{ (summary.avgConfidence || 0).toFixed(0) }}%</div>
      </div>
      <div class="rounded-lg border border-gray-200 bg-white p-4 text-center dark:border-gray-800 dark:bg-gray-900">
        <div class="text-xs text-gray-500">人数（最小/最大）</div>
        <div class="text-2xl font-semibold">{{ summary.minPeople }} / {{ summary.maxPeople }}</div>
      </div>
    </div>

    <RangeChart :data="data" />
  </div>
</template>

<style scoped>
</style>

