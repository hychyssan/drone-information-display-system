import { defineStore } from 'pinia'

export type FrameTelemetry = {
  timestamp: number
  peopleCount: number
  confidence: number // 0-100 范围的百分比数值
}

export type RecordingItem = {
  id: string
  title: string
  startTime: number
  endTime?: number
  fileUrl?: string
}

const MAX_POINTS_DEFAULT = 600 // 10min @ 1s

export const useTelemetryStore = defineStore('telemetry', {
  state: () => ({
    frames: [] as FrameTelemetry[],
    maxPoints: MAX_POINTS_DEFAULT,
    recordings: [] as RecordingItem[],
  }),
  getters: {
    latest: (s) => (s.frames.length ? s.frames[s.frames.length - 1] : null),
    avgConfidence: (s) => {
      if (!s.frames.length) return 0
      const sum = s.frames.reduce((acc, f) => acc + (Number.isFinite(f.confidence) ? f.confidence : 0), 0)
      return s.frames.length ? sum / s.frames.length : 0
    },
    maxPeople: (s) => s.frames.reduce((m, f) => Math.max(m, f.peopleCount), 0),
    minPeople: (s) => s.frames.reduce((m, f) => Math.min(m, f.peopleCount), s.frames.length ? s.frames[0].peopleCount : 0),
  },
  actions: {
    addFrame(frame: FrameTelemetry) {
      this.frames.push(frame)
      if (this.frames.length > this.maxPoints) {
        this.frames.splice(0, this.frames.length - this.maxPoints)
      }
    },
    clearFrames() {
      this.frames = []
    },
    getFramesInRange(startTime: number, endTime: number): FrameTelemetry[] {
      return this.frames.filter(f => f.timestamp >= startTime && f.timestamp <= endTime)
    },
    summarize(frames: FrameTelemetry[]) {
      if (!frames.length) {
        return { count: 0, avgConfidence: 0, maxPeople: 0, minPeople: 0 }
      }
      const count = frames.length
      const avgConfidence = frames.reduce((a, b) => a + b.confidence, 0) / count
      const maxPeople = frames.reduce((m, f) => Math.max(m, f.peopleCount), 0)
      const minPeople = frames.reduce((m, f) => Math.min(m, f.peopleCount), frames[0].peopleCount)
      return { count, avgConfidence, maxPeople, minPeople }
    },
    startRecording(title?: string) {
      const id = `${Date.now()}`
      this.recordings.unshift({ id, title: title || `录制 ${new Date().toLocaleString()}`, startTime: Date.now() })
      return id
    },
    stopRecording(id: string, fileUrl?: string) {
      const item = this.recordings.find(r => r.id === id)
      if (item) {
        item.endTime = Date.now()
        if (fileUrl) item.fileUrl = fileUrl
      }
    },
  },
})


