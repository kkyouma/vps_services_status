<script setup>
import TimelineBars from './TimelineBars.vue'

const props = defineProps({
  service: {
    type: Object,
    required: true
  }
})

function getStatusBadge(status) {
  switch (status) {
    case 'operational':
      return {
        label: 'Operational',
        color: 'text-[#74b946]',
      }
    case 'degraded':
      return {
        label: 'Degraded',
        color: 'text-[#e28725]',
      }
    case 'down':
      return {
        label: 'Major Outage',
        color: 'text-[#d6453d]',
      }
    default:
      return {
        label: 'Unknown',
        color: 'text-zinc-400',
      }
  }
}
</script>

<template>
  <div class="bg-[#181715] hover:bg-[#1a1917] transition-colors border border-[#262522] rounded-lg p-5 sm:p-6 shadow-sm">
    <!-- Top Header -->
    <div class="flex items-center justify-between mb-2">
      <div class="flex flex-col">
        <h3 class="text-base sm:text-lg font-medium text-[#eae9e5] tracking-tight">
          {{ service.name }}
        </h3>
        <p v-if="service.description" class="text-xs text-[#8c8a82] mt-0.5">
          {{ service.description }}
        </p>
      </div>

      <div class="flex items-center gap-2">
        <span
          class="text-sm sm:text-base font-medium tracking-tight"
          :class="getStatusBadge(service.current_status).color"
        >
          {{ getStatusBadge(service.current_status).label }}
        </span>
      </div>
    </div>

    <!-- 90 Days Timeline -->
    <TimelineBars
      :history="service.history || []"
      :uptime="service.uptime_90d_percentage || 100.0"
    />
  </div>
</template>
