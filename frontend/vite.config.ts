import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  // In production builds, VITE_API_URL must be set as an env var in Vercel
  // e.g. VITE_API_URL=https://gem-compliance-api.onrender.com
})
