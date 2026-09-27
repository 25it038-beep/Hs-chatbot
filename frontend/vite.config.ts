import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  envPrefix: ['VITE_', 'NEXT_PUBLIC_'],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      'next-themes': path.resolve(__dirname, './src/components/theme/ThemeProvider.tsx'),
    },
  },
  plugins: [
    react(),
    {
      name: 'serve-downloads-with-headers',
      configureServer(server) {
        server.middlewares.use((req, res, next) => {
          if (req.url && req.url.startsWith('/downloads/')) {
            const rawFilename = path.basename(req.url.split('?')[0])
            res.setHeader('Content-Disposition', `attachment; filename="${rawFilename}"`)
            res.setHeader('Access-Control-Allow-Origin', '*')
            res.setHeader('Cache-Control', 'public, max-age=3600')
          }
          next()
        })
      },
      configurePreviewServer(server) {
        server.middlewares.use((req, res, next) => {
          if (req.url && req.url.startsWith('/downloads/')) {
            const rawFilename = path.basename(req.url.split('?')[0])
            res.setHeader('Content-Disposition', `attachment; filename="${rawFilename}"`)
            res.setHeader('Access-Control-Allow-Origin', '*')
            res.setHeader('Cache-Control', 'public, max-age=3600')
          }
          next()
        })
      }
    }
  ],
  server: {
    port: 3000,
    host: '0.0.0.0',
    allowedHosts: true,
    proxy: {
      '/api': {
        target: process.env.VITE_API_URL || 'https://hs-chatbot-2.onrender.com',
        changeOrigin: true,
        secure: false,
        ws: true,
      },
    },
  },
  preview: {
    port: 3000,
    host: '0.0.0.0',
    allowedHosts: true,
  },
})
