<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import HeaderStatus from './components/HeaderStatus.vue'
import ServiceCard from './components/ServiceCard.vue'

const statusData = ref(null)
const isLoading = ref(false)
const error = ref(null)
let pollTimer = null

// Canonical domain redirect guard
if (
  typeof window !== 'undefined' &&
  window.location.hostname.endsWith('.pages.dev')
) {
  window.location.replace(
    'https://status.mimamita.site' +
      window.location.pathname +
      window.location.search
  )
}

// Fallback initial data in case status.json hasn't been generated yet
const defaultFallback = {
  title: 'System Status',
  description: 'Live operational status of VPS and Cloud infrastructure',
  last_updated: new Date().toISOString(),
  overall_status: 'operational',
  services: [
    {
      id: 'outline',
      name: 'Outline',
      category: 'VPS Core',
      description: 'Internal Knowledge Base & Wiki',
      current_status: 'operational',
      current_latency_ms: 320,
      current_message: 'HTTP 200',
      uptime_30d_percentage: 100.0,
      uptime_90d_percentage: 100.0,
      history: Array.from({ length: 30 }, (_, i) => ({
        date: new Date(Date.now() - (29 - i) * 86400000).toISOString().split('T')[0],
        status: i === 29 ? 'operational' : 'nodata',
        uptime_percentage: 100.0,
        avg_latency_ms: i === 29 ? 320 : 0,
        min_latency_ms: i === 29 ? 280 : 0,
        max_latency_ms: i === 29 ? 360 : 0,
        total_checks: i === 29 ? 24 : 0,
        down_checks: 0,
        hours: Array.from({ length: 24 }, (_, h) => ({
          hour: h,
          status: i === 29 ? 'operational' : 'nodata',
          avg_latency_ms: i === 29 ? 300 + Math.round(Math.sin(h) * 40) : 0,
          min_latency_ms: i === 29 ? 280 : 0,
          max_latency_ms: i === 29 ? 360 : 0,
          checks_count: i === 29 ? 1 : 0,
          down_checks: 0,
          degraded_checks: 0
        }))
      }))
    },
    {
      id: 'crm',
      name: 'CRM',
      category: 'VPS Core',
      description: 'Customer Relationship Management System',
      current_status: 'operational',
      current_latency_ms: 250,
      current_message: 'HTTP 200',
      uptime_30d_percentage: 100.0,
      uptime_90d_percentage: 100.0,
      history: Array.from({ length: 30 }, (_, i) => ({
        date: new Date(Date.now() - (29 - i) * 86400000).toISOString().split('T')[0],
        status: i === 29 ? 'operational' : 'nodata',
        uptime_percentage: 100.0,
        avg_latency_ms: i === 29 ? 250 : 0,
        min_latency_ms: i === 29 ? 210 : 0,
        max_latency_ms: i === 29 ? 290 : 0,
        total_checks: i === 29 ? 24 : 0,
        down_checks: 0,
        hours: Array.from({ length: 24 }, (_, h) => ({
          hour: h,
          status: i === 29 ? 'operational' : 'nodata',
          avg_latency_ms: i === 29 ? 240 + Math.round(Math.cos(h) * 30) : 0,
          min_latency_ms: i === 29 ? 210 : 0,
          max_latency_ms: i === 29 ? 290 : 0,
          checks_count: i === 29 ? 1 : 0,
          down_checks: 0,
          degraded_checks: 0
        }))
      }))
    }
  ]
}

async function fetchStatus(triggerLiveCheck = false) {
  isLoading.value = true
  error.value = null
  try {
    let res = null

    // If manual refresh was requested, attempt triggering live check on backend API
    if (triggerLiveCheck) {
      try {
        res = await fetch('/api/check', { method: 'POST' })
      } catch {
        res = null
      }
    }

    // If live check wasn't triggered or failed (e.g. static Cloudflare Pages), fetch status.json
    if (!res || !res.ok) {
      try {
        res = await fetch('/api/status')
      } catch {
        res = null
      }
    }

    if (!res || !res.ok) {
      res = await fetch('./data/status.json?t=' + Date.now())
    }

    if (!res.ok) {
      throw new Error(`Failed to load status: ${res.statusText}`)
    }
    const data = await res.json()
    statusData.value = data
  } catch (err) {
    console.warn('Could not fetch /api or /data/status.json, using fallback/local state:', err)
    if (!statusData.value) {
      statusData.value = defaultFallback
    }
  } finally {
    isLoading.value = false
  }
}

// Group services by category
const groupedServices = computed(() => {
  if (!statusData.value?.services) return {}
  const groups = {}
  for (const s of statusData.value.services) {
    const cat = s.category || 'General Services'
    if (!groups[cat]) {
      groups[cat] = []
    }
    groups[cat].push(s)
  }
  return groups
})

onMounted(() => {
  fetchStatus()
  // Poll every 30 seconds
  pollTimer = setInterval(fetchStatus, 30000)
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<template>
  <main class="min-h-screen bg-[#121211] text-[#d4d4d4] py-10 px-4 sm:px-6 lg:px-8">
    <div class="max-w-4xl mx-auto">
      <!-- Header -->
      <HeaderStatus
        :title="statusData?.title || 'System Status'"
        :description="statusData?.description || ''"
        :overall-status="statusData?.overall_status || 'operational'"
        :last-updated="statusData?.last_updated || ''"
        :is-loading="isLoading"
        @refresh="fetchStatus(true)"
      />

      <!-- Services List (Grouped or Direct Stack) -->
      <div class="space-y-8">
        <section
          v-for="(services, category) in groupedServices"
          :key="category"
          class="space-y-4"
        >
          <h2 class="text-xs font-semibold uppercase tracking-wider text-[#737169] px-1">
            {{ category }}
          </h2>

          <div class="space-y-4">
            <ServiceCard
              v-for="service in services"
              :key="service.id"
              :service="service"
            />
          </div>
        </section>
      </div>

      <!-- Footer -->
      <footer class="mt-16 pt-8 border-t border-[#262522] flex flex-col sm:flex-row items-center justify-between text-xs text-[#737169] gap-4">
        <div class="flex items-center gap-2">
          <span>State Panel</span>
          <span>•</span>
          <span class="text-[#8a8880]">Hosted on Cloudflare Pages</span>
        </div>
        <div class="flex items-center gap-4">
          <a
            href="https://github.com"
            target="_blank"
            rel="noopener noreferrer"
            class="hover:text-[#a1a098] transition-colors"
          >
            GitHub
          </a>
          <a
            href="./data/status.json"
            target="_blank"
            class="hover:text-[#a1a098] transition-colors"
          >
            Raw JSON API
          </a>
        </div>
      </footer>
    </div>
  </main>
</template>
