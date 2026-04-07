import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig, loadEnv } from 'vite'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')

  const devPort = Number(env.VITE_DEV_PORT) || 8513

  return {
    plugins: [react(), tailwindcss()],
    server: {
      port: devPort,
      strictPort: true,
      proxy: {
        '/api': {
          target: env.VITE_DEV_API_PROXY_TARGET || 'http://127.0.0.1:8512',
          changeOrigin: true,
        },
      },
    },
  }
})
