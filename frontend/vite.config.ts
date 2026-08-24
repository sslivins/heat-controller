import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    // Proxy API + WS calls to the goodhvac backend during `npm run dev` so
    // the SPA can call relative paths (/devices, /ws/status, ...) without
    // CORS or hardcoding a host:port.
    proxy: {
      '/devices': 'http://localhost:8010',
      '/tags': 'http://localhost:8010',
      '/ws': {
        target: 'ws://localhost:8010',
        ws: true,
      },
    },
  },
})
