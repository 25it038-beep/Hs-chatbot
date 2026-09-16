import React from 'react'
import ReactDOM from 'react-dom/client'
import { ThemeProvider } from '@/components/theme/ThemeProvider'
import { ClerkProvider } from '@clerk/clerk-react'
import { MotionConfigProvider } from '@/components/animations/MotionConfig'
import { CLERK_PUBLISHABLE_KEY, HAS_CLERK } from '@/lib/clerkConfig'
import App from './App'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
      <MotionConfigProvider>
        {HAS_CLERK && CLERK_PUBLISHABLE_KEY ? (
          <ClerkProvider
            publishableKey={CLERK_PUBLISHABLE_KEY}
            afterSignOutUrl="/"
            signInFallbackRedirectUrl="/"
            signUpFallbackRedirectUrl="/"
            signInForceRedirectUrl="/"
            signUpForceRedirectUrl="/"
          >
            <App />
          </ClerkProvider>
        ) : (
          <App />
        )}
      </MotionConfigProvider>
    </ThemeProvider>
  </React.StrictMode>,
)
