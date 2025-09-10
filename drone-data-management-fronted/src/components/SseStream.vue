<script setup lang="ts">
import { onMounted, onBeforeUnmount, ref, computed, watch } from 'vue'

type IncomingImageMetadata = Record<string, unknown>
type NormalizedImageMetadata = {
  timestamp: number
  centerX: number
  centerY: number
  width: number
  height: number
  confidence: number
}

const props = defineProps<{ reconnectIntervalMs?: number }>()
const reconnectIntervalMs = computed(() => props.reconnectIntervalMs ?? 5000)

const events = ref<NormalizedImageMetadata[]>([])
const connectionState = ref<'connecting' | 'open' | 'closed'>('connecting')
const lastUpdated = ref<Date | null>(null)
const minConfidence = ref<number>(0)
const eventSourceRef = ref<EventSource | null>(null)
const scrollContainer = ref<HTMLDivElement | null>(null)

const filteredEvents = computed(() => {
  return events.value.filter(e => e.confidence >= minConfidence.value)
})

function toNumber(value: unknown): number {
  if (typeof value === 'number') return value
  if (typeof value === 'string') {
    const n = Number(value)
    return Number.isFinite(n) ? n : NaN
  }
  return NaN
}

function normalizeMetadata(raw: IncomingImageMetadata): NormalizedImageMetadata | null {
  // 兼容 camelCase 与 snake_case
  const timestamp = toNumber(raw.timestamp ?? raw['timeStamp'])
  const centerX = toNumber(raw.centerX ?? raw['center_x'])
  const centerY = toNumber(raw.centerY ?? raw['center_y'])
  const width = toNumber(raw.width)
  const height = toNumber(raw.height)
  const confidence = toNumber(raw.confidence)

  if ([timestamp, centerX, centerY, width, height, confidence].some(v => Number.isNaN(v))) {
    return null
  }
  return { timestamp, centerX, centerY, width, height, confidence }
}

function openSse() {
  connectionState.value = 'connecting'
  const es = new EventSource('/api/image-metadata/stream')
  eventSourceRef.value = es

  es.onopen = () => {
    connectionState.value = 'open'
  }

  es.onmessage = (evt) => {
    try {
      const data = JSON.parse(evt.data) as IncomingImageMetadata
      const normalized = normalizeMetadata(data)
      if (!normalized) return
      events.value = [normalized, ...events.value]
      lastUpdated.value = new Date()
      queueMicrotask(() => {
        if (scrollContainer.value) {
          scrollContainer.value.scrollTo({ top: 0, behavior: 'smooth' })
        }
      })
    } catch (err) {
      // 忽略解析错误
    }
  }

  es.onerror = () => {
    es.close()
    connectionState.value = 'closed'
    scheduleReconnect()
  }
}

let reconnectTimer: number | null = null
function scheduleReconnect() {
  if (reconnectTimer) return
  reconnectTimer = window.setTimeout(() => {
    reconnectTimer = null
    openSse()
  }, reconnectIntervalMs.value)
}

function manualRefresh() {
  // 关闭旧连接并清空数据后重连
  if (eventSourceRef.value) {
    eventSourceRef.value.close()
    eventSourceRef.value = null
  }
  connectionState.value = 'connecting'
  events.value = []
  openSse()
}

function formatTimestamp(ts: number | string) {
  const n = Number(ts)
  if (!Number.isFinite(n)) return String(ts)
  return new Date(n).toLocaleString()
}

const connectionLabel = computed(() => {
  switch (connectionState.value) {
    case 'connecting':
      return '连接中'
    case 'open':
      return '已连接'
    default:
      return '断开'
  }
})

onMounted(() => {
  openSse()
})

onBeforeUnmount(() => {
  if (eventSourceRef.value) eventSourceRef.value.close()
  if (reconnectTimer) window.clearTimeout(reconnectTimer)
})

watch(reconnectIntervalMs, () => {
  // 如用户修改了间隔，重置自动重连计划
  if (reconnectTimer) {
    window.clearTimeout(reconnectTimer)
    reconnectTimer = null
  }
  if (connectionState.value === 'closed') scheduleReconnect()
})
</script>

<template>
  <div class="mx-auto max-w-5xl p-4">
    <div class="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <div class="flex items-center gap-2">
        <span class="text-sm text-gray-500">状态：</span>
        <span
          class="text-sm font-medium"
          :class="{
            'text-amber-600': connectionState === 'connecting',
            'text-green-600': connectionState === 'open',
            'text-red-600': connectionState === 'closed',
          }"
        >{{ connectionLabel }}</span>
        <button
          class="ml-3 rounded-md bg-blue-600 px-3 py-1.5 text-white text-sm hover:bg-blue-700 active:bg-blue-800"
          @click="manualRefresh"
        >手动刷新</button>
      </div>

      <div class="flex items-center gap-3">
        <label class="text-sm text-gray-600">置信度阈值: {{ minConfidence }}%</label>
        <input
          class="w-40"
          type="range"
          min="0"
          max="100"
          step="1"
          v-model.number="minConfidence"
        />
      </div>
    </div>

    <div class="mb-3 text-xs text-gray-500">
      最后更新时间：
      <span v-if="lastUpdated">{{ lastUpdated.toLocaleString() }}</span>
      <span v-else>—</span>
    </div>

    <div ref="scrollContainer" class="grid gap-3 overflow-auto" style="max-height: 60vh">
      <transition-group name="list" tag="div" class="grid gap-3">
        <div
          v-for="(item, idx) in filteredEvents"
          :key="`${item.timestamp}-${idx}`"
          class="rounded-lg border border-gray-200 bg-white shadow-sm transition hover:shadow-md dark:bg-gray-900 dark:border-gray-800"
        >
          <div class="flex items-center justify-between border-b border-gray-100 px-4 py-2 dark:border-gray-800">
            <div class="text-sm font-medium text-gray-700 dark:text-gray-200">{{ formatTimestamp(item.timestamp) }}</div>
            <div class="text-xs text-gray-500">置信度：{{ Number(item.confidence).toFixed(1) }}%</div>
          </div>
          <div class="grid grid-cols-2 gap-4 px-4 py-3 text-sm">
            <div class="space-y-1">
              <div class="text-gray-500">中心坐标</div>
              <div class="font-medium">x={{ item.centerX.toFixed(1) }}, y={{ item.centerY.toFixed(1) }}</div>
            </div>
            <div class="space-y-1">
              <div class="text-gray-500">框尺寸</div>
              <div class="font-medium">w={{ item.width.toFixed(1) }}, h={{ item.height.toFixed(1) }}</div>
            </div>
          </div>
        </div>
      </transition-group>
    </div>
  </div>
</template>

<style scoped>
.list-enter-active,
.list-leave-active {
  transition: all 0.25s ease;
}
.list-enter-from {
  opacity: 0;
  transform: translateY(-6px);
}
.list-enter-to {
  opacity: 1;
  transform: translateY(0px);
}
.list-leave-from {
  opacity: 1;
}
.list-leave-to {
  opacity: 0;
}
</style>

