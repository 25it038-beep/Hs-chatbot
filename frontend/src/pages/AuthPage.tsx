import React, { useState } from 'react'
import { SignIn, SignUp } from '@clerk/clerk-react'
import { useAuth } from '@/stores/auth'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Eye, EyeOff, UserCheck, KeyRound, Sparkles } from 'lucide-react'
import { cn } from '@/lib/utils'
import { HAS_CLERK } from '@/lib/clerkConfig'
import { setTokens } from '@/lib/api'

export function AuthPage() {
  const { login, register, loading } = useAuth()
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [authMethod, setAuthMethod] = useState<'clerk' | 'local'>(HAS_CLERK ? 'clerk' : 'local')
  const [email, setEmail] = useState('')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [showPassword, setShowPassword] = useState(false)

  React.useEffect(() => {
    const syncHash = () => {
      if (window.location.hash.includes('sign-up')) {
        setMode('register')
      } else if (window.location.hash.includes('sign-in')) {
        setMode('login')
      }
    }
    syncHash()
    window.addEventListener('hashchange', syncHash)
    return () => window.removeEventListener('hashchange', syncHash)
  }, [])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    try {
      if (mode === 'login') {
        await login(username, password)
      } else {
        await register(email, username, password)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong')
    }
  }

  const handleGuestLogin = () => {
    setTokens('hsbot_guest_token', '')
    useAuth.setState({
      user: {
        id: 'guest_' + Math.random().toString(36).substring(2, 8),
        username: 'Guest User',
        email: 'guest@hsbot.ai',
        display_name: 'Guest User',
        is_active: true,
        created_at: new Date().toISOString(),
      },
      initialized: true,
    })
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-3 sm:p-6 py-6 sm:py-10 relative z-10 overflow-y-auto pt-safe pb-safe">
      <div className="w-full max-w-sm sm:max-w-md animate-fade-in-up my-auto">
        <div className="text-center mb-6 sm:mb-8">
          <div className="w-14 h-14 sm:w-16 sm:h-16 rounded-xl overflow-hidden mx-auto mb-4 sm:mb-5 shadow-soft border border-border">
            <img src="/logo.jpg" alt="HSBot" className="w-full h-full object-cover" />
          </div>
          <h1 className="text-xl sm:text-2xl font-semibold tracking-tight">Welcome to HSBot</h1>
          <p className="text-xs sm:text-sm text-muted-foreground/70 mt-1.5">Your AI-powered assistant</p>
        </div>

        {HAS_CLERK && authMethod === 'clerk' ? (
          <div className="flex flex-col items-center gap-4">
            <div className="flex bg-muted/50 rounded-xl p-1 w-full max-w-sm">
              <button
                type="button"
                onClick={() => {
                  setMode('login')
                  window.location.hash = '#/sign-in'
                }}
                className={cn(
                  'flex-1 py-2 text-sm font-medium rounded-lg transition-all duration-200',
                  mode === 'login'
                    ? 'bg-background shadow-sm text-foreground'
                    : 'text-muted-foreground/60 hover:text-foreground'
                )}
              >
                Sign In
              </button>
              <button
                type="button"
                onClick={() => {
                  setMode('register')
                  window.location.hash = '#/sign-up'
                }}
                className={cn(
                  'flex-1 py-2 text-sm font-medium rounded-lg transition-all duration-200',
                  mode === 'register'
                    ? 'bg-background shadow-sm text-foreground'
                    : 'text-muted-foreground/60 hover:text-foreground'
                )}
              >
                Sign Up
              </button>
            </div>
            <div className="flex justify-center shadow-lg rounded-2xl overflow-hidden w-full">
              {mode === 'login' ? (
                <SignIn
                  routing="hash"
                  fallbackRedirectUrl="/"
                  signUpUrl="/#/sign-up"
                />
              ) : (
                <SignUp
                  routing="hash"
                  fallbackRedirectUrl="/"
                  signInUrl="/#/sign-in"
                />
              )}
            </div>

            {/* Quick Access / Alternate Options */}
            <div className="w-full flex flex-col gap-2.5 mt-2">
              <Button
                type="button"
                variant="outline"
                className="w-full h-10 rounded-xl text-xs font-medium border-border/80 hover:bg-muted/60 shadow-xs flex items-center justify-center gap-2"
                onClick={handleGuestLogin}
              >
                <Sparkles size={14} className="text-primary" />
                <span>Continue as Guest (Instant Access)</span>
              </Button>

              <button
                type="button"
                onClick={() => setAuthMethod('local')}
                className="text-xs text-muted-foreground hover:text-foreground transition-colors text-center py-1 flex items-center justify-center gap-1.5"
              >
                <KeyRound size={12} />
                <span>Sign in with HSBot username & password</span>
              </button>
            </div>
          </div>
        ) : (
          <div className="bg-card border border-border rounded-xl p-6 shadow-soft">
            <div className="flex bg-muted/50 rounded-xl p-1 mb-6">
              <button
                onClick={() => setMode('login')}
                className={cn(
                  'flex-1 py-2 text-sm font-medium rounded-lg transition-all duration-200',
                  mode === 'login'
                    ? 'bg-background shadow-sm text-foreground'
                    : 'text-muted-foreground/60 hover:text-foreground'
                )}
              >
                Sign In
              </button>
              <button
                onClick={() => setMode('register')}
                className={cn(
                  'flex-1 py-2 text-sm font-medium rounded-lg transition-all duration-200',
                  mode === 'register'
                    ? 'bg-background shadow-sm text-foreground'
                    : 'text-muted-foreground/60 hover:text-foreground'
                )}
              >
                Sign Up
              </button>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              {mode === 'register' && (
                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-muted-foreground/80 ml-1">Email</label>
                  <Input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="you@example.com"
                    required
                    className="h-10 rounded-xl"
                  />
                </div>
              )}
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-muted-foreground/80 ml-1">
                  {mode === 'login' ? 'Email or Username' : 'Username'}
                </label>
                <Input
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder={mode === 'login' ? 'you@example.com' : 'username'}
                  required
                  className="h-10 rounded-xl"
                />
              </div>
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-muted-foreground/80 ml-1">Password</label>
                <div className="relative">
                  <Input
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    required
                    minLength={mode === 'register' ? 8 : 1}
                    className="h-10 rounded-xl pr-10"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground/50 hover:text-foreground transition-colors"
                  >
                    {showPassword ? <EyeOff size={14} /> : <Eye size={14} />}
                  </button>
                </div>
              </div>

              {error && (
                <p className="text-xs text-destructive bg-destructive/5 px-3 py-2 rounded-lg">{error}</p>
              )}

              <Button type="submit" className="w-full h-10 rounded-lg bg-primary text-primary-foreground hover:opacity-90 shadow-soft" disabled={loading}>
                {loading ? (
                  <span className="flex items-center gap-2">
                    <span className="animate-spin w-4 h-4 border-2 border-background border-t-transparent rounded-full" />
                    {mode === 'login' ? 'Signing in...' : 'Creating account...'}
                  </span>
                ) : mode === 'login' ? 'Sign In' : 'Create Account'}
              </Button>

              <div className="relative my-4">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-border/60" />
                </div>
                <div className="relative flex justify-center text-xs">
                  <span className="bg-card px-2 text-muted-foreground/60">or</span>
                </div>
              </div>

              <Button
                type="button"
                variant="outline"
                className="w-full h-10 rounded-lg text-xs font-medium border-border/80 hover:bg-muted/50"
                onClick={handleGuestLogin}
              >
                <UserCheck size={14} className="mr-1.5 text-primary" />
                <span>Continue as Guest (Instant Access)</span>
              </Button>

              {HAS_CLERK && (
                <button
                  type="button"
                  onClick={() => setAuthMethod('clerk')}
                  className="w-full text-xs text-primary hover:underline text-center pt-2"
                >
                  ← Back to Clerk Sign In
                </button>
              )}
            </form>
          </div>
        )}

        <p className="text-xs text-muted-foreground/30 text-center mt-6">
          By continuing, you agree to our Terms of Service and Privacy Policy.
        </p>
      </div>
    </div>
  )
}
