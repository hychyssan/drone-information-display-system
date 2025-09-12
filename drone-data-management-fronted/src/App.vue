<script setup lang="ts">
import { ref } from 'vue'
import Dashboard from './pages/Dashboard.vue'
import Stats from './pages/Stats.vue'

const tab = ref<'dashboard' | 'stats'>('dashboard')
</script>

<template>
  <main class="min-h-screen bg-gray-50 text-gray-900 dark:bg-gray-950 dark:text-gray-100">
    <header class="border-b border-gray-200 bg-white/60 backdrop-blur-md dark:border-gray-800 dark:bg-gray-900/60">
      <div class="mx-auto flex max-w-5xl items-center justify-between p-4">
        <h1 class="text-lg font-semibold">无人机人像识别·实时数据</h1>
        <div class="flex items-center gap-2 text-sm">
          <button class="rounded px-2 py-1" :class="tab==='dashboard' ? 'bg-gray-900 text-white dark:bg-gray-100 dark:text-gray-900' : 'bg-gray-100 dark:bg-gray-800'" @click="tab='dashboard'">实时监控</button>
          <button class="rounded px-2 py-1" :class="tab==='stats' ? 'bg-gray-900 text-white dark:bg-gray-100 dark:text-gray-900' : 'bg-gray-100 dark:bg-gray-800'" @click="tab='stats'">统计</button>
        </div>
      </div>
    </header>
    <component :is="tab==='dashboard' ? Dashboard : Stats" />
  </main>
</template>

<style scoped>
</style>
