<script setup>
import { computed } from 'vue'

const props = defineProps({
  title: {
    type: String,
    default: 'System Status'
  },
  description: {
    type: String,
    default: ''
  },
  overallStatus: {
    type: String,
    default: 'operational'
  },
  lastUpdated: {
    type: String,
    default: ''
  },
  isLoading: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['refresh'])

const formattedLastUpdated = computed(() => {
  if (!props.lastUpdated) return 'Checking...'
  const date = new Date(props.lastUpdated)
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
})

const statusConfig = computed(() => {
  switch (props.overallStatus) {
    case 'operational':
      return {
        label: 'All Systems Operational',
        bannerBg: 'bg-[#18281a] border-[#27442a] text-[#48bb78]',
      }
    case 'degraded':
      return {
        label: 'Degraded System Performance',
        bannerBg: 'bg-[#281f14] border-[#4a361c] text-[#f59e0b]',
      }
    case 'major_outage':
    case 'down':
      return {
        label: 'Major System Outage',
        bannerBg: 'bg-[#281717] border-[#4a2222] text-[#ef4444]',
      }
    default:
      return {
        label: 'System Status Unknown',
        bannerBg: 'bg-[#1b1a18] border-[#2e2c28] text-zinc-400',
      }
  }
})
</script>

<template>
  <header class="mb-8 select-none">
    <!-- Top Meta Row -->
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-6">
      <div>
        <h1 class="text-2xl sm:text-3xl font-bold tracking-tight text-white flex items-center gap-3">
          {{ title }}
        </h1>
        <p v-if="description" class="text-sm text-[#8c8a82] mt-1">
          {{ description }}
        </p>
      </div>

      <div class="flex items-center gap-3 self-end sm:self-auto text-xs text-[#8c8a82]">
        <span>Uptime over the past 30 days.</span>
        <button
          class="p-1.5 hover:bg-[#262522] rounded-md transition-colors text-[#a1a098] hover:text-white"
          :title="isLoading ? 'Refreshing...' : 'Refresh status'"
          :disabled="isLoading"
          @click="emit('refresh')"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            class="w-4 h-4"
            :class="{ 'animate-spin': isLoading }"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" />
            <path d="M3 3v5h5" />
            <path d="M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16" />
            <path d="M16 21h5v-5" />
          </svg>
        </button>
      </div>
    </div>

    <!-- Main Overall Status Banner (Flat pleasant background, no dot) -->
    <div
      class="border rounded-lg px-5 py-3.5 flex items-center justify-between transition-colors"
      :class="statusConfig.bannerBg"
    >
      <span class="font-semibold text-sm sm:text-base tracking-tight">
        {{ statusConfig.label }}
      </span>

      <div class="text-xs opacity-75 font-mono">
        Updated {{ formattedLastUpdated }}
      </div>
    </div>
  </header>
</template>
