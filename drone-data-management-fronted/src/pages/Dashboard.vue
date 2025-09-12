<script setup lang="ts">
import { ref } from 'vue'
import VideoPlayer from '@/components/VideoPlayer.vue'
import SseStream from '@/components/SseStream.vue'

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
      <SseStream @latest="handleLatest" />
    </div>
  </div>
</template>

<style scoped>
</style>

