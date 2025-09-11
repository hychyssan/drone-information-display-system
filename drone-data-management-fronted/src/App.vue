<script setup lang="ts">
import SseStream from './components/SseStream.vue'
</script>

<template>
  <main class="min-h-screen bg-gray-50 text-gray-900 dark:bg-gray-950 dark:text-gray-100">
    <header class="border-b border-gray-200 bg-white/60 backdrop-blur-md dark:border-gray-800 dark:bg-gray-900/60">
      <div class="mx-auto flex max-w-5xl items-center justify-between p-4">
        <h1 class="text-lg font-semibold">无人机人像识别·实时数据</h1>
        <div class="text-xs text-gray-500">SSE 实时流</div>
      </div>
    </header>
    <SseStream />
  </main>
</template>

<style scoped>
</style>
