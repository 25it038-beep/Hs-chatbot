import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'
import { liveApiPlugin } from './server/liveApiPlugin'

export default defineConfig({
  plugins: [react(), liveApiPlugin()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      'next-themes': path.resolve(__dirname, './src/components/theme/ThemeProvider.tsx'),
    },
  },
  server: {
    port: 3000,
    host: '0.0.0.0',
    proxy: {
      // Fallback proxy to backend if running
      '/api/external': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        ws: true,
      },
    },
  },
})
