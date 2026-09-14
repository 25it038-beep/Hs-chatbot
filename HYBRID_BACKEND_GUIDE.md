# 🔄 Hybrid Backend Switching Guide

## What It Does

Your app now **automatically switches** between backends:

```
✅ Local Backend (localhost:8000)
   → When: Desktop app running locally + backend running
   → Speed: Fast (no network latency)
   → Use for: Development, offline work, certain tasks

✅ Render Backend (hs-chatbot-2.onrender.com)
   → When: Local backend unavailable or offline
   → Speed: Normal (includes network latency)
   → Use for: Production, when desktop app isn't running
```

---

## How It Works

### Priority Order:
1. **Check if online** → If offline, try local backend
2. **Try localhost:8000** → If responds to health check, use it
3. **Fall back to Render** → If local unavailable
4. **Offline mode** → Use cached/local if available

### Detection Logic:
- **First API call**: Detect active backend (2-second timeout on local check)
- **Cache result**: Valid for 30 seconds
- **Auto-refresh**: On network change (online ↔ offline)
- **Manual refresh**: Use `resetBackendCache()` in console

---

## File Changes

### 1. **New File: `frontend/src/lib/backendDetector.ts`**
   - Core detection logic
   - Functions:
     - `detectActiveBackend()` - Async detection with fallback
     - `getCurrentBackend()` - Get cached URL
     - `resetBackendCache()` - Force refresh
     - `setupBackendSwitcher()` - Listen to online/offline events

### 2. **Updated: `frontend/src/lib/api.ts`**
   - Added: `getBaseUrlAsync()` - Async backend detection
   - Updated all fetch calls to use async detection:
     - ✅ `request()` - Regular API calls
     - ✅ `sendMessageStream()` - Chat messages
     - ✅ `nvidiaChatStream()` - NVIDIA model calls
     - ✅ `uploadFile()` & `uploadMultiple()` - File uploads
     - ✅ `refreshAccessToken()` - Token refresh

---

## Usage Scenarios

### Scenario 1: Local Development
```
1. Start local backend: cd backend && uvicorn app.main:app --reload
2. Start frontend dev server: cd frontend && npm run dev
3. App opens → Detects local backend → Uses localhost:8000
✅ All requests hit local backend (fast)
```

### Scenario 2: Desktop App (Offline)
```
1. Backend running locally
2. Desktop app (Tauri) launches
3. No internet connection
4. App detects: offline + local backend available
✅ Chat works with local backend (fully offline mode)
```

### Scenario 3: Production (Render)
```
1. Build frontend without VITE_API_URL env var
2. Desktop app launches
3. First API call → Detects: local unavailable → Uses Render
✅ All requests go to Render backend
```

### Scenario 4: Hybrid (Desktop + Remote)
```
1. Backend running locally
2. Desktop app with INTERNET
3. First API call → Detects local backend
4. Browser/web user → Uses Render automatically
✅ Desktop gets fast local; web users get Render
```

---

## Configuration

### Environment Variables (Optional)

**Force a backend (bypass detection):**
```bash
# Use only local (for offline-only testing)
VITE_API_URL=http://localhost:8000

# Use only Render (for web-only testing)
VITE_API_URL=https://hs-chatbot-2.onrender.com

# Auto-detect (default - omit VITE_API_URL)
# (not set = uses hybrid detection)
```

### Detection Timeouts (in `backendDetector.ts`)

```typescript
const HEALTH_CHECK_TIMEOUT = 2000;      // How long to wait for local check
const CACHE_DURATION = 30000;            // Cache result for 30 seconds
```

---

## Console Commands (Developer Tools)

### Check Current Backend:
```javascript
// Browser console
import { getCurrentBackend } from './lib/backendDetector'
console.log(getCurrentBackend()) // http://localhost:8000 or https://...
```

### Force Refresh Detection:
```javascript
import { resetBackendCache, detectActiveBackend } from './lib/backendDetector'
resetBackendCache()
const url = await detectActiveBackend()
console.log('Active backend:', url)
```

### Listen for Changes:
```javascript
window.addEventListener('online', () => console.log('🌐 Online'))
window.addEventListener('offline', () => console.log('📡 Offline'))
```

---

## Advantages

| Scenario | Before | After |
|----------|--------|-------|
| Local dev | Manual env var switching | Auto-detects local |
| Desktop offline | Doesn't work | Works with local backend |
| Prod web | Single Render URL | Auto-uses Render |
| Hybrid (desktop + web) | Can't have both | Desktop local + web Render ✅ |
| Network drops | App breaks | Gracefully falls back |

---

## Testing

### Test 1: Verify Local Detection
```bash
# Terminal 1: Start backend
cd backend && uvicorn app.main:app --reload

# Terminal 2: Start frontend
cd frontend && npm run dev

# Open app → Check console for "🟢 Online: Local backend available"
```

### Test 2: Verify Render Fallback
```bash
# Stop local backend
# App should switch to Render → Check console for "🔵 Online: Local backend unavailable - using Render"
```

### Test 3: Offline Mode
```bash
# Disable network (or DevTools: Network → offline)
# With local backend running: Should work
# Without local backend: Should fail gracefully with error message
```

### Test 4: Network Changes
```javascript
// In DevTools console:
// Switch network to offline
window.dispatchEvent(new Event('offline'))
// Check: "📡 Network offline - will use cached or local backend"

// Switch back online
window.dispatchEvent(new Event('online'))
// Check: "🌐 Network online - refreshing backend detection"
```

---

## Troubleshooting

### Problem: Always uses Render, never detects local backend
**Solution:** Check if local backend is actually running and responding to `GET http://localhost:8000/api/health`

### Problem: App hangs on first API call
**Solution:** Local backend health check has 2s timeout. If it's taking longer, increase `HEALTH_CHECK_TIMEOUT` in `backendDetector.ts`

### Problem: Backend detection too slow
**Solution:** Adjust cache duration in `backendDetector.ts`:
```typescript
const CACHE_DURATION = 5000; // Shorter cache = more frequent checks
```

### Problem: Want to disable hybrid switching
**Solution:** Set env var:
```bash
VITE_API_URL=https://hs-chatbot-2.onrender.com
```

---

## Next Steps

1. **Test locally**: Start backend + frontend, verify "local backend" in console
2. **Test offline**: Stop backend, desktop app should fail gracefully
3. **Test Render**: Don't set VITE_API_URL, app should use Render
4. **Build desktop**: Desktop .exe will now auto-switch between backends! 

🎉 **Your app is now hybrid-enabled!**
