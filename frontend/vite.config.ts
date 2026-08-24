import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // Proxy API + WS calls to the heatctl backend during `npm run dev` so
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
