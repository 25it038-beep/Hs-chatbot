import React from 'react'
import ReactDOM from 'react-dom/client'
import { ThemeProvider } from 'next-themes'
import { MotionConfigProvider } from '@/components/animations/MotionConfig'
import App from './App'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ThemeProvider attribute="class" defaultTheme="system" enableSystem disableTransitionOnChange>
      <MotionConfigProvider>
        <App />
      </MotionConfigProvider>
    </ThemeProvider>
  </React.StrictMode>,
)
