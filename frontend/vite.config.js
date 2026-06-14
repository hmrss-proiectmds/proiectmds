import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.js'],
  },
  server: {
    proxy: {
      // WebSocket proxy — must be BEFORE the generic /api proxy
      // so that /api/games/ws/* is matched first
      '/api/games/ws': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        ws: true,
      },
      // REST API proxy — no ws flag to avoid conflicts with Vite's HMR socket
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/health': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/docs': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
