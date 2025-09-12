<script setup lang="ts">
import { ref } from 'vue'
import { useTelemetryStore } from '@/stores/telemetry'

const telemetry = useTelemetryStore()
const recordingId = ref<string | null>(null)
const isRecording = ref(false)

function start() {
  if (isRecording.value) return
  recordingId.value = telemetry.startRecording()
  isRecording.value = true
  // 这里预留触发后端开始录制的调用（可用 fetch/axios）
}

function stop() {
  if (!isRecording.value || !recordingId.value) return
  telemetry.stopRecording(recordingId.value)
  isRecording.value = false
  // 这里预留触发后端停止录制并返回文件地址
}
</script>

<template>
  <div class="flex items-center gap-3">
    <button
      class="rounded-md bg-red-600 px-3 py-1.5 text-white text-sm disabled:opacity-50"
      :disabled="isRecording"
      @click="start"
    >开始录制</button>
    <button
      class="rounded-md bg-gray-700 px-3 py-1.5 text-white text-sm disabled:opacity-50"
      :disabled="!isRecording"
      @click="stop"
    >停止录制</button>
    <span class="text-xs text-gray-500">{{ isRecording ? '录制中…' : '空闲' }}</span>
  </div>
</template>

<style scoped>
</style>

