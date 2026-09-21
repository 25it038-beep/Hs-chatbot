import React from 'react'
import ReactDOM from 'react-dom/client'
import { ThemeProvider } from '@/components/theme/ThemeProvider'
import { ClerkProvider } from '@clerk/clerk-react'
import { MotionConfigProvider } from '@/components/animations/MotionConfig'
import { CLERK_PUBLISHABLE_KEY, HAS_CLERK } from '@/lib/clerkConfig'
import App from './App'
import './index.css'

const routerNavigate = (to: string, replace = false) => {
  if (!to) {
    if (window.location.hash) {
      window.location.hash = ''
      window.history.replaceState(null, '', window.location.pathname || '/')
      window.dispatchEvent(new HashChangeEvent('hashchange'))
    }
    return
  }

  try {
    const targetUrl = new URL(to, window.location.origin)
    if (targetUrl.origin === window.location.origin) {
      const pathname = targetUrl.pathname || '/'
      const hash = targetUrl.hash || ''

      // Handle hash-based routing (e.g. /#/sign-in, #/sign-up)
      if (hash.startsWith('#/sign-') || hash.startsWith('#sign-')) {
        if (replace) {
          window.location.replace(hash)
        } else {
          window.location.hash = hash
        }
        window.dispatchEvent(new HashChangeEvent('hashchange'))
        return
      }

      // Root / application destination
      if (pathname === '/' && (!hash || hash === '#' || hash === '#/')) {
        if (window.location.hash) {
          window.location.hash = ''
          window.history.replaceState(null, '', '/')
          window.dispatchEvent(new HashChangeEvent('hashchange'))
        }
        if (window.location.search.includes('__clerk') || window.location.pathname !== '/') {
          if (replace) {
            window.location.replace('/')
          } else {
            window.location.assign('/')
          }
        }
        return
      }

      const dest = pathname + targetUrl.search + hash
      if (replace) {
        window.location.replace(dest)
      } else {
        window.location.assign(dest)
      }
      return
    }
  } catch {
    // Fallback if URL constructor fails
  }

  if (replace) {
    window.location.replace(to)
  } else {
    window.location.assign(to)
  }
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
      <MotionConfigProvider>
        {HAS_CLERK && CLERK_PUBLISHABLE_KEY ? (
          <ClerkProvider
            publishableKey={CLERK_PUBLISHABLE_KEY}
            routerPush={(to) => routerNavigate(to, false)}
            routerReplace={(to) => routerNavigate(to, true)}
            afterSignOutUrl="/"
            signInForceRedirectUrl="/"
            signUpForceRedirectUrl="/"
            signInFallbackRedirectUrl="/"
            signUpFallbackRedirectUrl="/"
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
