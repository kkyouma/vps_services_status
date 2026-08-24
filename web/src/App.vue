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

// Fallback initial data structure (clean empty state while loading)
const defaultFallback = {
  title: 'System Status',
  description: 'Live operational status of VPS and Cloud infrastructure',
  last_updated: new Date().toISOString(),
  overall_status: 'operational',
  services: []
}

async function fetchStatus(triggerLiveCheck = false) {
  isLoading.value = true
  error.value = null
  try {
    let data = null

    // 1. If manual live check was triggered, try POST /api/check
    if (triggerLiveCheck) {
      try {
        const res = await fetch('/api/check', { method: 'POST' })
        const contentType = res.headers.get('content-type') || ''
        if (res.ok && contentType.includes('application/json')) {
          data = await res.json()
        }
      } catch {
        data = null
      }
    }

    // 2. Primary: Cloudflare Pages Edge Function (/api/status)
    if (!data) {
      try {
        const res = await fetch('/api/status')
        const contentType = res.headers.get('content-type') || ''
        if (res.ok && (contentType.includes('application/json') || contentType.includes('text/json'))) {
          const parsed = await res.json()
          if (parsed && Array.isArray(parsed.services) && parsed.services.length > 0) {
            data = parsed
          }
        }
      } catch {
        data = null
      }
    }

    // 3. Fallback: Static ./data/status.json (for offline / local builds / fallback)
    if (!data) {
      try {
        const res = await fetch('./data/status.json?t=' + Date.now())
        const contentType = res.headers.get('content-type') || ''
        if (res.ok && (contentType.includes('application/json') || contentType === '' || contentType.includes('text/plain'))) {
          const parsed = await res.json()
          if (parsed && Array.isArray(parsed.services) && parsed.services.length > 0) {
            data = parsed
          }
        }
      } catch {
        data = null
      }
    }

    if (data) {
      statusData.value = data
    } else {
      throw new Error('Failed to load valid status JSON')
    }
  } catch (err) {
    console.warn('Could not fetch status data:', err)
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
