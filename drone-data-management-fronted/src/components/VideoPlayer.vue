<script setup lang="ts">
import Hls from 'hls.js'
import { onMounted, onBeforeUnmount, ref, watch, computed } from 'vue'

type OverlayData = {
  peopleCount?: number
  timestamp?: number
  centerX?: number
  centerY?: number
  width?: number
  height?: number
  confidence?: number
}

const props = defineProps<{
  src: string
  autoplay?: boolean
  muted?: boolean
  controls?: boolean
  overlay?: OverlayData | null
}>()

const videoRef = ref<HTMLVideoElement | null>(null)
let hls: Hls | null = null

const canUseNativeHls = computed(() => {
  const v = document.createElement('video')
  return v.canPlayType('application/vnd.apple.mpegurl') !== ''
})

function attach() {
  const video = videoRef.value
  if (!video) return
  if (canUseNativeHls.value) {
    video.src = props.src
    return
  }
  if (Hls.isSupported()) {
    hls = new Hls({ enableWorker: true })
    hls.loadSource(props.src)
    hls.attachMedia(video)
    hls.on(Hls.Events.ERROR, (_evt, data) => {
      if (data.fatal && hls) {
        switch (data.type) {
          case Hls.ErrorTypes.NETWORK_ERROR:
            hls.startLoad()
            break
          case Hls.ErrorTypes.MEDIA_ERROR:
            hls.recoverMediaError()
            break
          default:
            hls.destroy(); hls = null
        }
      }
    })
  } else {
    // 浏览器不支持 HLS
    console.warn('HLS not supported in this browser')
  }
}

function detach() {
  if (hls) {
    hls.destroy()
    hls = null
  }
}

onMounted(() => {
  attach()
})

onBeforeUnmount(() => {
  detach()
})

watch(() => props.src, () => {
  detach(); attach()
})
</script>

<template>
  <div class="relative w-full overflow-hidden rounded-lg border border-gray-200 bg-black dark:border-gray-800">
    <video
      ref="videoRef"
      :autoplay="props.autoplay ?? true"
      :muted="props.muted ?? true"
      :controls="props.controls ?? true"
      playsinline
      class="block h-[360px] w-full bg-black object-contain sm:h-[420px]"
    ></video>

    <div v-if="overlay" class="pointer-events-none absolute inset-0 select-none">
      <div class="absolute left-2 top-2 rounded bg-black/50 px-2 py-1 text-xs text-white">
        人数：{{ overlay?.peopleCount ?? 0 }}
      </div>
      <div class="absolute left-2 top-8 rounded bg-black/50 px-2 py-1 text-[10px] text-white space-x-2">
        <span>置信度：{{ overlay?.confidence?.toFixed?.(1) ?? '-' }}%</span>
        <span>坐标：x={{ overlay?.centerX?.toFixed?.(1) ?? '-' }}, y={{ overlay?.centerY?.toFixed?.(1) ?? '-' }}</span>
        <span>尺寸：w={{ overlay?.width?.toFixed?.(1) ?? '-' }}, h={{ overlay?.height?.toFixed?.(1) ?? '-' }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
</style>

