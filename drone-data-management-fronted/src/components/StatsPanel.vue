<script setup lang="ts">
import { computed } from 'vue'
import { useTelemetryStore } from '@/stores/telemetry'

const telemetry = useTelemetryStore()
const latest = computed(() => telemetry.latest)
const avg = computed(() => telemetry.avgConfidence)
</script>

<template>
  <div class="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900">
    <div class="grid grid-cols-3 gap-4 text-center">
      <div>
        <div class="text-xs text-gray-500">当前人数</div>
        <div class="text-2xl font-semibold">{{ latest?.peopleCount ?? 0 }}</div>
      </div>
      <div>
        <div class="text-xs text-gray-500">平均置信度</div>
        <div class="text-2xl font-semibold">{{ avg.toFixed(0) }}%</div>
      </div>
      <div>
        <div class="text-xs text-gray-500">时间戳</div>
        <div class="text-sm">{{ latest?.timestamp ? new Date(latest.timestamp).toLocaleString() : '—' }}</div>
      </div>
    </div>
  </div>
</template>

<style scoped>
</style>

