/**
 * Hybrid Backend Detector
 * 
 * Intelligently switches between local backend (dev/offline)
 * and Render backend (production/online)
 */

const LOCAL_BACKEND = "http://localhost:8000";
const RENDER_BACKEND = "https://hs-chatbot-2.onrender.com";
const HEALTH_CHECK_TIMEOUT = 2000; // 2 second timeout for local backend check

let cachedBackendUrl: string | null = null;
let lastCheckTime = 0;
const CACHE_DURATION = 30000; // Cache result for 30 seconds

/**
 * Check if local backend is available
 */
async function isLocalBackendAvailable(): Promise<boolean> {
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), HEALTH_CHECK_TIMEOUT);

    const response = await fetch(`${LOCAL_BACKEND}/api/health`, {
      method: "GET",
      signal: controller.signal,
    });

    clearTimeout(timeoutId);
    return response.ok;
  } catch (error) {
    // Local backend not available
    return false;
  }
}

/**
 * Detect active backend with smart fallback
 * 
 * Priority:
 * 1. Local backend if running AND online (for browser automation + faster chat)
 * 2. Render backend otherwise (chat-only, browser disabled on Render free tier)
 */
export async function detectActiveBackend(forceRefresh = false): Promise<string> {
  // Return cached result if still valid
  if (cachedBackendUrl && !forceRefresh && Date.now() - lastCheckTime < CACHE_DURATION) {
    return cachedBackendUrl
  }

  // Check if online
  const isOnline = navigator.onLine

  // If offline, try to use local backend
  if (!isOnline) {
    const localAvailable = await isLocalBackendAvailable()
    if (localAvailable) {
      cachedBackendUrl = LOCAL_BACKEND
      lastCheckTime = Date.now()
      console.log("🔴 Offline: Using local backend (browser enabled)")
      return LOCAL_BACKEND
    }
    // Offline and local unavailable - still return Render (will fail gracefully)
    cachedBackendUrl = RENDER_BACKEND
    lastCheckTime = Date.now()
    console.log("🔴 Offline: Local backend unavailable, using Render (browser disabled)")
    return RENDER_BACKEND
  }

  // Online: prefer local for browser automation, fall back to Render for chat
  const localAvailable = await isLocalBackendAvailable()

  if (localAvailable) {
    cachedBackendUrl = LOCAL_BACKEND
    lastCheckTime = Date.now()
    console.log("🟢 Online: Local backend available - using local (browser enabled)")
    return LOCAL_BACKEND
  }

  // Local unavailable, use Render (chat-only, no browser)
  cachedBackendUrl = RENDER_BACKEND
  lastCheckTime = Date.now()
  console.log("🔵 Online: Local backend unavailable - using Render (browser disabled)")
  return RENDER_BACKEND
}

/**
 * Get current backend URL (uses cache, no fresh detection)
 */
export function getCurrentBackend(): string {
  if (cachedBackendUrl) {
    return cachedBackendUrl;
  }
  // Default to Render if not detected yet
  return RENDER_BACKEND;
}

/**
 * Force reset cache (useful for testing)
 */
export function resetBackendCache(): void {
  cachedBackendUrl = null;
  lastCheckTime = 0;
}

/**
 * Listen to online/offline changes and refresh
 */
export function setupBackendSwitcher(): void {
  window.addEventListener("online", () => {
    console.log("🌐 Network online - refreshing backend detection");
    resetBackendCache();
  });

  window.addEventListener("offline", () => {
    console.log("📡 Network offline - will use cached or local backend");
    resetBackendCache();
  });
}
