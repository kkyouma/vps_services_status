<script setup>
import { ref } from 'vue'

const props = defineProps({
  history: {
    type: Array,
    required: true,
    default: () => []
  },
  uptime: {
    type: Number,
    required: true,
    default: 100.0
  }
})

const hoveredDay = ref(null)
const tooltipX = ref(0)

function getBarColor(status) {
  switch (status) {
    case 'operational':
      return 'bg-[#74b946]'
    case 'degraded':
      return 'bg-[#e28725]'
    case 'down':
      return 'bg-[#d6453d]'
    default:
      return 'bg-[#2d2c27]'
  }
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  const date = new Date(dateStr + 'T00:00:00Z')
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    timeZone: 'UTC'
  })
}

function handleMouseEnter(day, event) {
  hoveredDay.value = day
  const rect = event.currentTarget.getBoundingClientRect()
  const parentRect = event.currentTarget.parentElement.getBoundingClientRect()
  tooltipX.value = rect.left - parentRect.left + (rect.width / 2)
}

function handleMouseLeave() {
  hoveredDay.value = null
}
</script>

<template>
  <div class="relative w-full select-none">
    <!-- Tooltip -->
    <div
      v-if="hoveredDay"
      class="absolute -top-16 z-30 transform -translate-x-1/2 bg-[#1f1e1b] border border-[#3a3832] text-xs rounded shadow-2xl px-3 py-1.5 pointer-events-none whitespace-nowrap"
      :style="{ left: `${tooltipX}px` }"
    >
      <div class="font-semibold text-white flex items-center gap-1.5">
        <span
          class="w-2 h-2 rounded-full inline-block"
          :class="{
            'bg-[#74b946]': hoveredDay.status === 'operational',
            'bg-[#e28725]': hoveredDay.status === 'degraded',
            'bg-[#d6453d]': hoveredDay.status === 'down',
            'bg-zinc-600': hoveredDay.status === 'nodata'
          }"
        ></span>
        {{ formatDate(hoveredDay.date) }}
      </div>
      <div class="text-[#a1a1aa] text-[11px] mt-0.5 flex items-center gap-2">
        <span>{{ hoveredDay.uptime_percentage }}% uptime</span>
        <span v-if="hoveredDay.avg_latency_ms > 0">• {{ hoveredDay.avg_latency_ms }} ms avg</span>
        <span v-if="hoveredDay.down_checks > 0" class="text-red-400 font-medium">
          • {{ hoveredDay.down_checks }} incidents
        </span>
      </div>
      <div class="tooltip-arrow"></div>
    </div>

    <!-- 30 Bars Container -->
    <div class="flex items-center justify-between gap-[3px] h-9 w-full my-3">
      <div
        v-for="(day, index) in history"
        :key="day.date || index"
        class="timeline-bar flex-1 h-full rounded-[2px] cursor-pointer"
        :class="getBarColor(day.status)"
        @mouseenter="handleMouseEnter(day, $event)"
        @mouseleave="handleMouseLeave"
      ></div>
    </div>

    <!-- Bottom Scale (30 days ago --- Uptime % --- Today) -->
    <div class="flex items-center justify-between text-xs text-[#8a8880] pt-1">
      <span class="text-[11px] text-[#737169]">30 days ago</span>
      <div class="flex-1 mx-3 flex items-center justify-center relative">
        <div class="w-full border-t border-[#2a2824]"></div>
        <span class="absolute bg-[#181715] px-3 text-[11px] text-[#9c9990] font-mono">
          {{ uptime.toFixed(2) }} % uptime
        </span>
      </div>
      <span class="text-[11px] text-[#737169]">Today</span>
    </div>
  </div>
</template>
