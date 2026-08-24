import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { readFileSync, existsSync } from 'fs'
import { resolve } from 'path'

function tursoDevPlugin() {
  return {
    name: 'turso-dev-server',
    configureServer(server) {
      server.middlewares.use(async (req, res, next) => {
        if (req.url === '/api/status' || req.url?.startsWith('/api/status?')) {
          const env = { ...process.env }
          const envPath = resolve(__dirname, '../.env')
          if (existsSync(envPath)) {
            const content = readFileSync(envPath, 'utf-8')
            for (const line of content.split('\n')) {
              const trimmed = line.trim()
              if (trimmed && !trimmed.startsWith('#') && trimmed.includes('=')) {
                const [k, ...v] = trimmed.split('=')
                env[k.trim()] = v.join('=').trim().replace(/^['"]|['"]$/g, '')
              }
            }
          }

          if (env.TURSO_DATABASE_URL && env.TURSO_AUTH_TOKEN) {
            try {
              const statusModule = await import('../functions/api/status.js')
              const fakeContext = {
                env: {
                  TURSO_DATABASE_URL: env.TURSO_DATABASE_URL,
                  TURSO_AUTH_TOKEN: env.TURSO_AUTH_TOKEN
                },
                request: { url: `http://${req.headers.host}${req.url}` },
                waitUntil: () => {}
              }
              globalThis.caches = globalThis.caches || {
                default: {
                  match: async () => null,
                  put: async () => {}
                }
              }
              const response = await statusModule.onRequestGet(fakeContext)
              const body = await response.text()
              res.statusCode = response.status
              res.setHeader('Content-Type', 'application/json')
              res.end(body)
              return
            } catch (err) {
              console.warn('[vite-turso-dev] Error in dev /api/status:', err)
            }
          }
        }
        next()
      })
    }
  }
}

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [vue(), tursoDevPlugin()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: process.env.VITE_API_URL || 'http://localhost:8000',
        changeOrigin: true
      }
    }
  },
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    sourcemap: false
  }
})
