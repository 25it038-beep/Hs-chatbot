/**
 * Helper to validate and configure Clerk Authentication safely.
 * Prevents runtime crashes from invalid or placeholder keys like "pk_test_...".
 */

export function isValidClerkPublishableKey(key?: string | null): boolean {
  if (!key || typeof key !== 'string') return false
  const trimmed = key.trim()

  // Must have a valid prefix
  if (!trimmed.startsWith('pk_test_') && !trimmed.startsWith('pk_live_')) {
    return false
  }

  // Reject placeholder values or ellipses
  if (trimmed.includes('...') || trimmed.length < 25) {
    return false
  }

  const parts = trimmed.split('_')
  if (parts.length !== 3 || !parts[2] || parts[2].includes('.')) {
    return false
  }

  try {
    const decoded = atob(parts[2])
    // Clerk publishable key payload ends with '$' and contains a host like 'clerk.example.com$'
    if (!decoded.endsWith('$')) return false
    const withoutTrailing = decoded.slice(0, -1)
    if (withoutTrailing.includes('$')) return false
    return withoutTrailing.includes('.')
  } catch {
    return false
  }
}

const rawEnvKey =
  (import.meta.env.VITE_CLERK_PUBLISHABLE_KEY as string | undefined) ||
  (import.meta.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY as string | undefined) ||
  ''

export const IS_VALID_CLERK_KEY = isValidClerkPublishableKey(rawEnvKey)
export const CLERK_PUBLISHABLE_KEY = IS_VALID_CLERK_KEY ? rawEnvKey.trim() : ''
export const HAS_CLERK = IS_VALID_CLERK_KEY
