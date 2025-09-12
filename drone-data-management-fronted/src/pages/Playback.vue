<script setup lang="ts">
import { computed, ref } from 'vue'
import VideoPlayer from '@/components/VideoPlayer.vue'
import RealtimeChart from '@/components/RealtimeChart.vue'
import StatsPanel from '@/components/StatsPanel.vue'
import { useTelemetryStore } from '@/stores/telemetry'

const props = defineProps<{ id?: string }>()
const telemetry = useTelemetryStore()
const selectedId = ref<string | null>(props.id ?? null)
const selected = computed(() => telemetry.recordings.find(r => r.id === selectedId.value) || null)

const src = computed(() => selected.value?.fileUrl || '')

</script>

<template>
  <div class="mx-auto max-w-6xl p-4">
    <div class="mb-3 text-sm">回放：<span class="font-medium">{{ selected?.title || '未选择' }}</span></div>
    <div class="grid gap-4 lg:grid-cols-2 items-start">
      <VideoPlayer v-if="src" :src="src" :controls="true" :autoplay="false" :muted="false" />
      <div v-else class="rounded border p-6 text-center text-sm text-gray-500 dark:border-gray-800 dark:bg-gray-900">请选择一条历史记录</div>
      <div class="space-y-3">
        <StatsPanel />
        <RealtimeChart />
      </div>
    </div>
  </div>
</template>

<style scoped>
</style>

