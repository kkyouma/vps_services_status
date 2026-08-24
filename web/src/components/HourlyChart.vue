<script setup>
import { ref, computed } from 'vue'
import { X, Activity, Clock, AlertCircle, CheckCircle2 } from 'lucide-vue-next'

const props = defineProps({
  day: {
    type: Object,
    required: true
  },
  serviceName: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['close'])

const hoveredHour = ref(null)

// Format date label
const formattedDate = computed(() => {
  if (!props.day?.date) return ''
  const d = new Date(props.day.date + 'T00:00:00Z')
  return d.toLocaleDateString('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    timeZone: 'UTC'
  })
})

// Extract hours (always guarantee 24 slots)
const hoursData = computed(() => {
  const rawHours = props.day?.hours || []
  const result = []
  for (let i = 0; i < 24; i++) {
    const found = rawHours.find((h) => h.hour === i)
    if (found) {
      result.push(found)
    } else {
      result.push({
        hour: i,
        status: 'nodata',
        avg_latency_ms: 0,
        min_latency_ms: 0,
        max_latency_ms: 0,
        checks_count: 0,
        down_checks: 0,
        degraded_checks: 0
      })
    }
  }
  return result
})

// Metrics summary
const maxLatency = computed(() => {
  const valid = hoursData.value
    .filter((h) => h.status !== 'nodata' && h.avg_latency_ms > 0)
    .map((h) => h.max_latency_ms || h.avg_latency_ms)
  return valid.length > 0 ? Math.max(...valid) : 50
})

const minLatency = computed(() => {
  const valid = hoursData.value
    .filter((h) => h.status !== 'nodata' && h.avg_latency_ms > 0)
    .map((h) => h.min_latency_ms || h.avg_latency_ms)
  return valid.length > 0 ? Math.min(...valid) : 0
})

// Chart dimensions
const chartWidth = 600
const chartHeight = 140
const padLeft = 40
const padRight = 20
const padTop = 15
const padBottom = 25

const usableWidth = chartWidth - padLeft - padRight
const usableHeight = chartHeight - padTop - padBottom

// Scale ceiling with nice padding
const yCeil = computed(() => {
  const maxVal = maxLatency.value
  if (maxVal <= 50) return 60
  if (maxVal <= 100) return 120
  if (maxVal <= 300) return 350
  if (maxVal <= 800) return 900
  return Math.ceil((maxVal * 1.25) / 100) * 100
})

// Coordinates for each hour
const points = computed(() => {
  return hoursData.value.map((h, i) => {
    const x = padLeft + (i / 23) * usableWidth
    const lat = h.status === 'nodata' ? 0 : h.avg_latency_ms
    const y =
      padTop + usableHeight - (Math.min(lat, yCeil.value) / yCeil.value) * usableHeight
    return {
      x,
      y,
      data: h,
      index: i
    }
  })
})

// SVG path generator (only connects hours with recorded checks)
const svgPath = computed(() => {
  const pts = points.value.filter(
    (p) => p.data.status !== 'nodata' && p.data.checks_count > 0
  )
  if (pts.length === 0) return ''
  if (pts.length === 1) return `M ${pts[0].x} ${pts[0].y}`

  let path = `M ${pts[0].x} ${pts[0].y}`
  for (let i = 1; i < pts.length; i++) {
    const prev = pts[i - 1]
    const curr = pts[i]
    // Smooth cubic bezier curve
    const cpx1 = prev.x + (curr.x - prev.x) / 2
    const cpy1 = prev.y
    const cpx2 = prev.x + (curr.x - prev.x) / 2
    const cpy2 = curr.y
    path += ` C ${cpx1} ${cpy1}, ${cpx2} ${cpy2}, ${curr.x} ${curr.y}`
  }
  return path
})

// SVG area generator (gradient fill)
const svgArea = computed(() => {
  const pts = points.value.filter(
    (p) => p.data.status !== 'nodata' && p.data.checks_count > 0
  )
  if (pts.length <= 1) return ''
  const baseY = padTop + usableHeight
  const lineP = svgPath.value
  return `${lineP} L ${pts[pts.length - 1].x} ${baseY} L ${pts[0].x} ${baseY} Z`
})

function formatHourLabel(hour) {
  return String(hour).padStart(2, '0') + ':00'
}

function getStatusBadge(status) {
  switch (status) {
    case 'operational':
      return { text: 'Operational', color: 'text-[#74b946]', bg: 'bg-[#74b946]' }
    case 'degraded':
      return { text: 'Degraded', color: 'text-[#e28725]', bg: 'bg-[#e28725]' }
    case 'down':
      return { text: 'Down', color: 'text-[#d6453d]', bg: 'bg-[#d6453d]' }
    default:
      return { text: 'No Data', color: 'text-[#737169]', bg: 'bg-[#2d2c27]' }
  }
}
</script>

<template>
  <div class="mt-4 pt-4 border-t border-[#262522] bg-[#141312] rounded-lg p-4 transition-all">
    <!-- Header -->
    <div class="flex items-center justify-between pb-3 border-b border-[#262522] mb-3">
      <div class="flex items-center gap-3">
        <div class="flex items-center gap-2">
          <Clock class="w-4 h-4 text-[#8a8880]" />
          <span class="text-sm font-semibold text-[#eae9e5]">
            24h Detail: {{ formattedDate }}
          </span>
        </div>
        <span
          class="text-xs px-2 py-0.5 rounded font-medium"
          :class="{
            'bg-[#74b946]/10 text-[#74b946] border border-[#74b946]/30': day.status === 'operational',
            'bg-[#e28725]/10 text-[#e28725] border border-[#e28725]/30': day.status === 'degraded',
            'bg-[#d6453d]/10 text-[#d6453d] border border-[#d6453d]/30': day.status === 'down',
            'bg-zinc-800 text-zinc-400': day.status === 'nodata'
          }"
        >
          {{ getStatusBadge(day.status).text }}
        </span>
      </div>

      <button
        @click="emit('close')"
        class="p-1 rounded text-[#8a8880] hover:text-[#eae9e5] hover:bg-[#262522] transition-colors"
        title="Close details"
      >
        <X class="w-4 h-4" />
      </button>
    </div>

    <!-- Summary Stats Bar -->
    <div class="grid grid-cols-2 sm:grid-cols-4 gap-2 mb-4 text-xs">
      <div class="bg-[#1b1a18] p-2.5 rounded border border-[#2a2824]">
        <div class="text-[#737169] text-[11px]">Uptime</div>
        <div class="text-[#eae9e5] font-mono font-semibold text-sm mt-0.5">
          {{ day.uptime_percentage ?? 100 }}%
        </div>
      </div>
      <div class="bg-[#1b1a18] p-2.5 rounded border border-[#2a2824]">
        <div class="text-[#737169] text-[11px]">Avg Latency</div>
        <div class="text-[#eae9e5] font-mono font-semibold text-sm mt-0.5">
          {{ day.avg_latency_ms > 0 ? `${day.avg_latency_ms} ms` : '-' }}
        </div>
      </div>
      <div class="bg-[#1b1a18] p-2.5 rounded border border-[#2a2824]">
        <div class="text-[#737169] text-[11px]">Max Peak</div>
        <div class="text-[#eae9e5] font-mono font-semibold text-sm mt-0.5">
          {{ day.max_latency_ms > 0 ? `${day.max_latency_ms} ms` : '-' }}
        </div>
      </div>
      <div class="bg-[#1b1a18] p-2.5 rounded border border-[#2a2824]">
        <div class="text-[#737169] text-[11px]">Total Checks</div>
        <div class="text-[#eae9e5] font-mono font-semibold text-sm mt-0.5">
          {{ day.total_checks ?? 0 }}
          <span v-if="day.down_checks > 0" class="text-red-400 font-normal text-[11px]">
            ({{ day.down_checks }} down)
          </span>
        </div>
      </div>
    </div>

    <!-- SVG Latency Chart -->
    <div class="relative w-full overflow-hidden bg-[#181715] rounded border border-[#262522] p-2 mb-3">
      <div class="flex items-center justify-between text-[11px] text-[#737169] px-2 mb-1">
        <span class="flex items-center gap-1.5">
          <Activity class="w-3.5 h-3.5 text-emerald-400" />
          Latency Trend (ms / hour)
        </span>
        <span v-if="hoveredHour !== null" class="font-mono text-emerald-400">
          {{ formatHourLabel(hoveredHour.hour) }}:
          <template v-if="hoveredHour.checks_count > 0">
            <strong class="text-white">{{ hoveredHour.avg_latency_ms }} ms</strong>
            ({{ getStatusBadge(hoveredHour.status).text }})
          </template>
          <template v-else>
            <span class="text-[#737169]">(No checks recorded yet)</span>
          </template>
        </span>
        <span v-else class="text-[#5a5852]">Hover to inspect hour</span>
      </div>

      <svg
        :viewBox="`0 0 ${chartWidth} ${chartHeight}`"
        class="w-full h-32 sm:h-36 overflow-visible"
      >
        <defs>
          <linearGradient id="latencyGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#74b946" stop-opacity="0.35" />
            <stop offset="100%" stop-color="#74b946" stop-opacity="0.0" />
          </linearGradient>
        </defs>

        <!-- Grid Lines -->
        <line
          :x1="padLeft"
          :y1="padTop"
          :x2="chartWidth - padRight"
          :y2="padTop"
          stroke="#262522"
          stroke-dasharray="3,3"
        />
        <text
          :x="padLeft - 6"
          :y="padTop + 4"
          fill="#5a5852"
          font-size="9"
          text-anchor="end"
          font-family="monospace"
        >
          {{ yCeil }}ms
        </text>

        <line
          :x1="padLeft"
          :y1="padTop + usableHeight / 2"
          :x2="chartWidth - padRight"
          :y2="padTop + usableHeight / 2"
          stroke="#262522"
          stroke-dasharray="3,3"
        />
        <text
          :x="padLeft - 6"
          :y="padTop + usableHeight / 2 + 3"
          fill="#5a5852"
          font-size="9"
          text-anchor="end"
          font-family="monospace"
        >
          {{ Math.round(yCeil / 2) }}ms
        </text>

        <line
          :x1="padLeft"
          :y1="padTop + usableHeight"
          :x2="chartWidth - padRight"
          :y2="padTop + usableHeight"
          stroke="#2a2824"
        />
        <text
          :x="padLeft - 6"
          :y="padTop + usableHeight + 3"
          fill="#5a5852"
          font-size="9"
          text-anchor="end"
          font-family="monospace"
        >
          0ms
        </text>

        <!-- Filled Area -->
        <path
          v-if="svgArea"
          :d="svgArea"
          fill="url(#latencyGradient)"
        />

        <!-- Curve Line -->
        <path
          v-if="svgPath"
          :d="svgPath"
          fill="none"
          stroke="#74b946"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
        />

        <!-- Data Points and Hover Vertical Guide -->
        <g v-for="pt in points" :key="pt.index">
          <!-- Active Vertical Guide -->
          <line
            v-if="hoveredHour && hoveredHour.hour === pt.data.hour"
            :x1="pt.x"
            :y1="padTop"
            :x2="pt.x"
            :y2="padTop + usableHeight"
            stroke="#74b946"
            stroke-width="1"
            stroke-dasharray="2,2"
          />

          <!-- Point Dot -->
          <circle
            v-if="pt.data.status !== 'nodata'"
            :cx="pt.x"
            :cy="pt.y"
            :r="hoveredHour && hoveredHour.hour === pt.data.hour ? 4.5 : 2"
            :fill="
              pt.data.status === 'operational'
                ? '#74b946'
                : pt.data.status === 'degraded'
                ? '#e28725'
                : '#d6453d'
            "
            :stroke="hoveredHour && hoveredHour.hour === pt.data.hour ? '#ffffff' : '#181715'"
            stroke-width="1.5"
            class="transition-all duration-150"
          />

          <!-- Invisible Click / Hover Slice -->
          <rect
            :x="pt.x - usableWidth / 48"
            :y="padTop"
            :width="usableWidth / 24"
            :height="usableHeight"
            fill="transparent"
            class="cursor-pointer"
            @mouseenter="hoveredHour = pt.data"
            @mouseleave="hoveredHour = null"
          />
        </g>

        <!-- X-Axis Hour Labels -->
        <g font-size="9" fill="#737169" font-family="monospace" text-anchor="middle">
          <text :x="padLeft" :y="chartHeight - 6">00:00</text>
          <text :x="padLeft + (4 / 23) * usableWidth" :y="chartHeight - 6">04:00</text>
          <text :x="padLeft + (8 / 23) * usableWidth" :y="chartHeight - 6">08:00</text>
          <text :x="padLeft + (12 / 23) * usableWidth" :y="chartHeight - 6">12:00</text>
          <text :x="padLeft + (16 / 23) * usableWidth" :y="chartHeight - 6">16:00</text>
          <text :x="padLeft + (20 / 23) * usableWidth" :y="chartHeight - 6">20:00</text>
          <text :x="chartWidth - padRight" :y="chartHeight - 6">23:00</text>
        </g>
      </svg>
    </div>

    <!-- 24-Hour Status Strip -->
    <div class="mt-2">
      <div class="text-[11px] text-[#737169] mb-1.5 flex items-center justify-between">
        <span>24h Status Strip (00:00 → 23:00)</span>
        <span v-if="hoveredHour" class="text-white font-mono text-[10px]">
          {{ formatHourLabel(hoveredHour.hour) }}: {{ hoveredHour.checks_count > 0 ? `${hoveredHour.checks_count} checks` : 'No checks' }}
        </span>
      </div>
      <div class="flex items-center gap-[2px] h-4 w-full">
        <div
          v-for="h in hoursData"
          :key="h.hour"
          class="flex-1 h-full rounded-[1px] cursor-pointer transition-transform hover:scale-y-125"
          :class="[
            getStatusBadge(h.status).bg,
            hoveredHour && hoveredHour.hour === h.hour ? 'ring-1 ring-white' : ''
          ]"
          :title="`${formatHourLabel(h.hour)}: ${getStatusBadge(h.status).text} (${h.avg_latency_ms} ms, ${h.checks_count} checks)`"
          @mouseenter="hoveredHour = h"
          @mouseleave="hoveredHour = null"
        ></div>
      </div>
    </div>
  </div>
</template>
