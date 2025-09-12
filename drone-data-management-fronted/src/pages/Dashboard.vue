<script setup lang="ts">
import { ref } from 'vue'
import VideoPlayer from '@/components/VideoPlayer.vue'
import SseStream from '@/components/SseStream.vue'
import StatsPanel from '@/components/StatsPanel.vue'
import RealtimeChart from '@/components/RealtimeChart.vue'
import RecorderControls from '@/components/RecorderControls.vue'
import HistoryList from '@/components/HistoryList.vue'

type Overlay = {
  peopleCount?: number
  timestamp?: number
  centerX?: number
  centerY?: number
  width?: number
  height?: number
  confidence?: number
}

const latest = ref<Overlay | null>(null)
function handleLatest(data: Overlay) {
  latest.value = data
}

const HLS_SRC = 'http://124.71.162.119:8081/hls/stream.m3u8'
</script>

<template>
  <div class="mx-auto max-w-6xl p-4">
    <div class="grid gap-4 lg:grid-cols-2 items-start">
      <VideoPlayer :src="HLS_SRC" :overlay="latest" />
      <div class="space-y-3">
        <div class="flex items-center justify-between">
          <div class="text-sm text-gray-600">实时工具</div>
          <RecorderControls />
        </div>
        <StatsPanel />
        <RealtimeChart />
        <SseStream @latest="handleLatest" />
        <HistoryList />
      </div>
    </div>
  </div>
</template>

<style scoped>
</style>

