import { defineConfig, type PluginOption } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig(async ({ command }) => {
  const plugins: PluginOption[] = [react()]

  if (command === 'serve') {
    try {
      const { liveApiPlugin } = await import('./server/liveApiPlugin')
      plugins.push(liveApiPlugin())
    } catch (err) {
      console.warn('[Vite] Could not load liveApiPlugin in dev mode:', err)
    }
  }

  return {
    plugins,
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
  }
})
