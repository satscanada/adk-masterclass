import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig, loadEnv } from 'vite'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')

  const devPort = Number(env.VITE_DEV_PORT) || 8513
  // Listen on all interfaces for LAN testing: VITE_DEV_HOST=0.0.0.0 npm run dev
  const rawHost = (env.VITE_DEV_HOST || '').trim()
  const devHost =
    rawHost === 'true' || rawHost === '1'
      ? true
      : rawHost === 'false' || rawHost === '0'
        ? false
        : rawHost || undefined

  return {
    plugins: [react(), tailwindcss()],
    server: {
      port: devPort,
      strictPort: true,
      ...(devHost !== undefined ? { host: devHost } : {}),
      proxy: {
        '/api': {
          target: env.VITE_DEV_API_PROXY_TARGET || 'http://127.0.0.1:8512',
          changeOrigin: true,
        },
      },
    },
  }
})
