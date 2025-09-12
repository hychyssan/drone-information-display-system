<script setup lang="ts">
import { computed, ref } from 'vue'
import { useTelemetryStore } from '@/stores/telemetry'

const telemetry = useTelemetryStore()
const query = ref('')
const items = computed(() => {
  const q = query.value.trim()
  const list = telemetry.recordings.slice().sort((a, b) => (b.startTime || 0) - (a.startTime || 0))
  if (!q) return list
  return list.filter(i => i.title.includes(q))
})

const emit = defineEmits<{ (e: 'select', id: string): void }>()
function select(id: string) {
  emit('select', id)
}
</script>

<template>
  <div class="rounded-lg border border-gray-200 bg-white p-3 dark:border-gray-800 dark:bg-gray-900">
    <div class="mb-2 flex items-center gap-2">
      <input v-model="query" placeholder="搜索标题…" class="w-full rounded border px-2 py-1 text-sm dark:bg-gray-800" />
    </div>
    <div class="max-h-64 overflow-auto">
      <div
        v-for="rec in items"
        :key="rec.id"
        class="cursor-pointer rounded px-2 py-2 hover:bg-gray-50 dark:hover:bg-gray-800"
        @click="select(rec.id)"
      >
        <div class="text-sm font-medium">{{ rec.title }}</div>
        <div class="text-xs text-gray-500">{{ new Date(rec.startTime).toLocaleString() }}
          <span v-if="rec.endTime"> — {{ new Date(rec.endTime).toLocaleString() }}</span>
        </div>
      </div>
      <div v-if="!items.length" class="py-6 text-center text-xs text-gray-500">暂无记录</div>
    </div>
  </div>
  
</template>

<style scoped>
</style>

