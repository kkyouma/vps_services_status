<script setup>
import { ref, computed } from 'vue'
import { X, Activity, Clock } from 'lucide-vue-next'

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

// Hover states
const hoveredPoint = ref(null)
const hoveredHourIndex = ref(null)

// Local timezone detection
const timeZoneShort = computed(() => {
  try {
    const str = new Date().toLocaleTimeString([], { timeZoneName: 'short' })
    const parts = str.split(' ')
    return parts[parts.length - 1] || ''
  } catch {
    return ''
  }
})

// Format date in local timezone
const formattedDate = computed(() => {
  if (!props.day?.date) return ''
  const d = new Date(props.day.date + 'T12:00:00Z')
  return d.toLocaleDateString([], {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    year: 'numeric'
  })
})

// Check if selected day is today in local time
const isToday = computed(() => {
  if (!props.day?.date) return false
  const now = new Date()
  const todayStr = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`
  return props.day.date === todayStr
})

// Current time marker position
const currentLocalTime = computed(() => {
  const now = new Date()
  const frac = now.getHours() + now.getMinutes() / 60 + now.getSeconds() / 3600
  return {
    hour: now.getHours(),
    minute: now.getMinutes(),
    fracHour: frac,
    timeStr: now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  }
})

// Extract all individual check points for granular visualization
const allCheckRecords = computed(() => {
  const list = []
  const rawHours = props.day?.hours || []
  for (const h of rawHours) {
    if (Array.isArray(h.checks) && h.checks.length > 0) {
      for (const c of h.checks) {
        list.push(c)
      }
    }
  }
  return list.sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime())
})

// Timezone offset in hours (e.g., GMT-4 has +4 hours offset behind UTC)
const tzOffsetHours = computed(() => {
  return Math.round(new Date().getTimezoneOffset() / 60)
})

// Build 24 hour slots in USER LOCAL TIME (00:00 to 23:00 Local)
const localHoursData = computed(() => {
  const result = []

  // If we have granular check records: group directly by local hour
  if (allCheckRecords.value.length > 0) {
    for (let h = 0; h < 24; h++) {
      const checksInHour = allCheckRecords.value.filter((c) => {
        const d = new Date(c.timestamp)
        return d.getHours() === h
      })

      if (checksInHour.length === 0) {
        result.push({
          hour: h,
          status: 'nodata',
          avg_latency_ms: 0,
          min_latency_ms: 0,
          max_latency_ms: 0,
          checks_count: 0,
          down_checks: 0,
          degraded_checks: 0,
          checks: []
        })
      } else {
        const count = checksInHour.length
        const totalLat = checksInHour.reduce((sum, c) => sum + (Number(c.latency_ms) || 0), 0)
        const lats = checksInHour.map((c) => Number(c.latency_ms) || 0)
        const downCount = checksInHour.filter((c) => c.status === 'down').length
        const degradedCount = checksInHour.filter((c) => c.status === 'degraded').length

        let status = 'operational'
        if (downCount === 0 && degradedCount === 0) {
          status = 'operational'
        } else if (downCount / count > 0.25) {
          status = 'down'
        } else {
          status = 'degraded'
        }

        result.push({
          hour: h,
          status,
          avg_latency_ms: Math.round((totalLat / count) * 100) / 100,
          min_latency_ms: Math.min(...lats),
          max_latency_ms: Math.max(...lats),
          checks_count: count,
          down_checks: downCount,
          degraded_checks: degradedCount,
          checks: checksInHour
        })
      }
    }
    return result
  }

  // Fallback: If no granular checks array, convert backend UTC hour slots to local hours
  const rawHours = props.day?.hours || []
  const offset = tzOffsetHours.value
  for (let localH = 0; localH < 24; localH++) {
    // Local hour localH corresponds to UTC hour: (localH + offset + 24) % 24
    const utcH = (localH + offset + 24) % 24
    const found = rawHours.find((h) => h.hour === utcH)
    if (found && found.checks_count > 0) {
      result.push({
        ...found,
        hour: localH
      })
    } else {
      result.push({
        hour: localH,
        status: 'nodata',
        avg_latency_ms: 0,
        min_latency_ms: 0,
        max_latency_ms: 0,
        checks_count: 0,
        down_checks: 0,
        degraded_checks: 0,
        checks: []
      })
    }
  }
  return result
})

// Chart dimensions
const chartWidth = 640
const chartHeight = 150
const padLeft = 42
const padRight = 24
const padTop = 20
const padBottom = 26

const usableWidth = chartWidth - padLeft - padRight
const usableHeight = chartHeight - padTop - padBottom

// Metrics summary for scaling
const maxLatency = computed(() => {
  if (allCheckRecords.value.length > 0) {
    const lats = allCheckRecords.value.map((c) => Number(c.latency_ms) || 0)
    return Math.max(...lats, 50)
  }
  const valid = localHoursData.value
    .filter((h) => h.status !== 'nodata' && h.avg_latency_ms > 0)
    .map((h) => h.max_latency_ms || h.avg_latency_ms)
  return valid.length > 0 ? Math.max(...valid) : 50
})

// Scale ceiling with clean grid intervals
const yCeil = computed(() => {
  const maxVal = maxLatency.value
  if (maxVal <= 50) return 60
  if (maxVal <= 100) return 120
  if (maxVal <= 300) return 350
  if (maxVal <= 800) return 900
  if (maxVal <= 1500) return 1600
  return Math.ceil((maxVal * 1.25) / 100) * 100
})

// Mapped SVG coordinates for granular check points in LOCAL TIME
const checkPoints = computed(() => {
  if (allCheckRecords.value.length > 0) {
    return allCheckRecords.value.map((c, i) => {
      const d = new Date(c.timestamp)
      // Convert to local fractional hour (0.00 to 23.99)
      const localHour = d.getHours()
      const localMin = d.getMinutes()
      const localSec = d.getSeconds()
      const frac = localHour + localMin / 60 + localSec / 3600

      const x = padLeft + (frac / 24) * usableWidth
      const lat = Number(c.latency_ms) || 0
      const y = padTop + usableHeight - (Math.min(lat, yCeil.value) / yCeil.value) * usableHeight

      return {
        id: `check-${c.timestamp}-${i}`,
        x,
        y,
        latency_ms: lat,
        status: c.status || 'operational',
        status_code: c.status_code || 200,
        message: c.message || 'HTTP 200',
        timestamp: c.timestamp,
        localTimeStr: d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
        hourIndex: localHour,
        fracHour: frac,
        isPoint: true
      }
    })
  }

  // Fallback: hourly averages in local time
  const activeHours = localHoursData.value.filter((h) => h.status !== 'nodata' && h.checks_count > 0)
  return activeHours.map((h) => {
    const x = padLeft + ((h.hour + 0.5) / 24) * usableWidth
    const lat = h.avg_latency_ms
    const y = padTop + usableHeight - (Math.min(lat, yCeil.value) / yCeil.value) * usableHeight

    return {
      id: `hour-${h.hour}`,
      x,
      y,
      latency_ms: lat,
      status: h.status,
      status_code: 200,
      message: `${h.checks_count} checks recorded`,
      timestamp: '',
      localTimeStr: `${String(h.hour).padStart(2, '0')}:00`,
      hourIndex: h.hour,
      fracHour: h.hour + 0.5,
      isPoint: false
    }
  })
})

// Current time marker X coordinate
const nowMarkerX = computed(() => {
  if (!isToday.value) return null
  return padLeft + (currentLocalTime.value.fracHour / 24) * usableWidth
})

// SVG path generator connecting all points smoothly
const svgPath = computed(() => {
  const pts = checkPoints.value
  if (pts.length === 0) return ''
  if (pts.length === 1) return `M ${pts[0].x} ${pts[0].y}`

  let path = `M ${pts[0].x} ${pts[0].y}`
  for (let i = 1; i < pts.length; i++) {
    const prev = pts[i - 1]
    const curr = pts[i]
    // Cubic bezier smoothing
    const cpx1 = prev.x + (curr.x - prev.x) / 2
    const cpy1 = prev.y
    const cpx2 = prev.x + (curr.x - prev.x) / 2
    const cpy2 = curr.y
    path += ` C ${cpx1} ${cpy1}, ${cpx2} ${cpy2}, ${curr.x} ${curr.y}`
  }
  return path
})

// SVG area gradient fill
const svgArea = computed(() => {
  const pts = checkPoints.value
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
      return { text: 'Major Outage', color: 'text-[#d6453d]', bg: 'bg-[#d6453d]' }
    default:
      return { text: 'No Data', color: 'text-[#737169]', bg: 'bg-[#2d2c27]' }
  }
}

// Active hour for sync
const activeHour = computed(() => {
  if (hoveredHourIndex.value !== null) {
    return localHoursData.value.find((h) => h.hour === hoveredHourIndex.value) || null
  }
  if (hoveredPoint.value) {
    return localHoursData.value.find((h) => h.hour === hoveredPoint.value.hourIndex) || null
  }
  return null
})
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
          <span v-if="timeZoneShort" class="text-[11px] text-[#737169] bg-[#1c1b18] px-1.5 py-0.5 rounded border border-[#2a2824] font-mono">
            {{ timeZoneShort }} (Local)
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
        <div class="text-[#737169] text-[11px]">Recorded Probes</div>
        <div class="text-[#eae9e5] font-mono font-semibold text-sm mt-0.5">
          {{ day.total_checks ?? allCheckRecords.length }}
          <span v-if="day.down_checks > 0" class="text-red-400 font-normal text-[11px]">
            ({{ day.down_checks }} down)
          </span>
        </div>
      </div>
    </div>

    <!-- SVG Latency Chart -->
    <div class="relative w-full overflow-hidden bg-[#181715] rounded border border-[#262522] p-2 mb-3">
      <!-- Live inspection readout header -->
      <div class="flex items-center justify-between text-[11px] text-[#737169] px-2 mb-1">
        <span class="flex items-center gap-1.5">
          <Activity class="w-3.5 h-3.5 text-[#74b946]" />
          Latency Trend (ms / probe)
        </span>

        <!-- Hover inspection readout -->
        <span v-if="hoveredPoint !== null" class="font-mono flex items-center gap-1.5 text-xs">
          <span class="text-[#8c8a82]">{{ hoveredPoint.localTimeStr }}:</span>
          <strong class="text-white">{{ hoveredPoint.latency_ms }} ms</strong>
          <span
            class="px-1.5 py-0.2 rounded text-[10px]"
            :class="{
              'bg-[#74b946]/20 text-[#74b946]': hoveredPoint.status === 'operational',
              'bg-[#e28725]/20 text-[#e28725]': hoveredPoint.status === 'degraded',
              'bg-[#d6453d]/20 text-[#d6453d]': hoveredPoint.status === 'down'
            }"
          >
            {{ hoveredPoint.message || getStatusBadge(hoveredPoint.status).text }}
          </span>
        </span>
        <span v-else-if="activeHour !== null" class="font-mono text-[#eae9e5]">
          {{ formatHourLabel(activeHour.hour) }}:
          <template v-if="activeHour.checks_count > 0">
            <strong class="text-[#74b946]">{{ activeHour.avg_latency_ms }} ms avg</strong>
            <span class="text-[#737169] text-[10px]"> ({{ activeHour.checks_count }} checks)</span>
          </template>
          <template v-else>
            <span class="text-[#737169]">(No checks recorded)</span>
          </template>
        </span>
        <span v-else></span>
      </div>

      <svg
        :viewBox="`0 0 ${chartWidth} ${chartHeight}`"
        class="w-full h-36 sm:h-40 overflow-visible select-none"
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

        <!-- Shaded Hour Range Band when hovering an hour in the strip -->
        <rect
          v-if="hoveredHourIndex !== null"
          :x="padLeft + (hoveredHourIndex / 24) * usableWidth"
          :y="padTop"
          :width="usableWidth / 24"
          :height="usableHeight"
          fill="#74b946"
          fill-opacity="0.10"
          stroke="#74b946"
          stroke-opacity="0.35"
          stroke-width="1"
          stroke-dasharray="2,2"
        />

        <!-- Filled Curve Area -->
        <path
          v-if="svgArea"
          :d="svgArea"
          fill="url(#latencyGradient)"
        />

        <!-- Smooth Curve Line -->
        <path
          v-if="svgPath"
          :d="svgPath"
          fill="none"
          stroke="#74b946"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
        />

        <!-- NOW Vertical Guide Line (Present time reference) -->
        <line
          v-if="nowMarkerX !== null"
          :x1="nowMarkerX"
          :y1="padTop"
          :x2="nowMarkerX"
          :y2="padTop + usableHeight"
          stroke="#71717a"
          stroke-width="1.5"
          stroke-dasharray="3,3"
        />

        <!-- Active Hovered Point Vertical Guide Line -->
        <line
          v-if="hoveredPoint"
          :x1="hoveredPoint.x"
          :y1="padTop"
          :x2="hoveredPoint.x"
          :y2="padTop + usableHeight"
          stroke="#74b946"
          stroke-width="1"
          stroke-dasharray="2,2"
        />

        <!-- All Individual Data Point Dots in Local Time -->
        <g v-for="pt in checkPoints" :key="pt.id">
          <!-- Point circle dot -->
          <circle
            :cx="pt.x"
            :cy="pt.y"
            :r="hoveredPoint && hoveredPoint.id === pt.id ? 5.5 : 2.5"
            :fill="
              pt.status === 'operational'
                ? '#74b946'
                : pt.status === 'degraded'
                ? '#e28725'
                : '#d6453d'
            "
            :stroke="hoveredPoint && hoveredPoint.id === pt.id ? '#ffffff' : '#141312'"
            :stroke-width="hoveredPoint && hoveredPoint.id === pt.id ? 2 : 1"
            class="transition-all duration-100"
          />

          <!-- Invisible large hover target for each point -->
          <circle
            :cx="pt.x"
            :cy="pt.y"
            r="10"
            fill="transparent"
            class="cursor-pointer"
            @mouseenter="hoveredPoint = pt"
            @mouseleave="hoveredPoint = null"
          />
        </g>

        <!-- X-Axis 24-Hour Local Labels -->
        <g font-size="9" fill="#737169" font-family="monospace" text-anchor="middle">
          <text :x="padLeft" :y="chartHeight - 7">00:00</text>
          <text :x="padLeft + (4 / 24) * usableWidth" :y="chartHeight - 7">04:00</text>
          <text :x="padLeft + (8 / 24) * usableWidth" :y="chartHeight - 7">08:00</text>
          <text :x="padLeft + (12 / 24) * usableWidth" :y="chartHeight - 7">12:00</text>
          <text :x="padLeft + (16 / 24) * usableWidth" :y="chartHeight - 7">16:00</text>
          <text :x="padLeft + (20 / 24) * usableWidth" :y="chartHeight - 7">20:00</text>
          <text :x="padLeft + usableWidth" :y="chartHeight - 7">23:59</text>
        </g>
      </svg>
    </div>

    <!-- 24-Hour Status Strip (Synced with Latency Chart in LOCAL TIME) -->
    <div class="mt-3">
      <div class="text-[11px] text-[#737169] mb-1.5 flex items-center justify-between">
        <span class="flex items-center gap-1.5">
          <span>24h Hourly Strip (00:00 → 23:00 Local)</span>
          <span class="text-[10px] text-[#5a5852]">• Colors: Green (0% down), Orange (&le;25% down), Red (&gt;25% down)</span>
        </span>
        <span v-if="activeHour" class="text-white font-mono text-[10px]">
          {{ formatHourLabel(activeHour.hour) }}:
          {{ activeHour.checks_count > 0 ? `${activeHour.checks_count} checks (${getStatusBadge(activeHour.status).text})` : 'No checks' }}
        </span>
      </div>

      <!-- Strip Bars in Local Time -->
      <div class="flex items-center gap-[2px] h-4 w-full">
        <div
          v-for="h in localHoursData"
          :key="h.hour"
          class="flex-1 h-full rounded-[1px] cursor-pointer transition-all relative"
          :class="[
            getStatusBadge(h.status).bg,
            activeHour && activeHour.hour === h.hour
              ? 'ring-1 ring-white scale-y-125 z-10 shadow-sm shadow-black'
              : 'hover:scale-y-110 hover:brightness-125',
            isToday && currentLocalTime.hour === h.hour ? 'border-b-2 border-zinc-400' : ''
          ]"
          :title="`${formatHourLabel(h.hour)}: ${getStatusBadge(h.status).text} (${h.avg_latency_ms} ms avg, ${h.checks_count} checks)`"
          @mouseenter="hoveredHourIndex = h.hour"
          @mouseleave="hoveredHourIndex = null"
        >
          <!-- Small indicator dot for current hour -->
          <div
            v-if="isToday && currentLocalTime.hour === h.hour"
            class="absolute -bottom-1.5 left-1/2 -translate-x-1/2 w-1 h-1 bg-zinc-400 rounded-full pointer-events-none"
          ></div>
        </div>
      </div>
    </div>
  </div>
</template>
