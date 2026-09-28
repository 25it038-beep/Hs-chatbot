/**
 * Resilient Downloader Utility for HSBot
 * Handles standalone downloads, iframe-sandboxed environments, blob streams, and progress tracking.
 */

export interface DownloadProgress {
  loaded: number
  total: number
  percent: number
  status: 'idle' | 'downloading' | 'completed' | 'error' | 'blocked'
  errorMessage?: string
}

export interface DownloadOptions {
  onProgress?: (progress: DownloadProgress) => void
  filename?: string
  fallbackUrls?: string[]
}

export function formatBytes(bytes: number, decimals = 1): string {
  if (!bytes || bytes === 0) return '0 B'
  const k = 1024
  const dm = decimals < 0 ? 0 : decimals
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(dm))} ${sizes[i]}`
}

export function getFullDownloadUrl(path = '/downloads/HSBot_1.0.0_x64-setup.exe'): string {
  if (path.startsWith('http://') || path.startsWith('https://')) {
    return path
  }
  const origin = window.location.origin
  return `${origin}${path.startsWith('/') ? '' : '/'}${path}`
}

export async function downloadWindowsInstaller(options?: DownloadOptions): Promise<boolean> {
  const filename = options?.filename || 'HSBot_1.0.0_x64-setup.exe'
  const primaryUrl = '/downloads/HSBot_1.0.0_x64-setup.exe'
  const fallbackUrls = options?.fallbackUrls || [
    primaryUrl,
    '/api/download/windows',
    'https://hs-chatbot-2.onrender.com/api/download/windows',
  ]

  const report = (p: Partial<DownloadProgress>) => {
    options?.onProgress?.({
      loaded: p.loaded ?? 0,
      total: p.total ?? 4252272,
      percent: p.percent ?? 0,
      status: p.status ?? 'downloading',
      errorMessage: p.errorMessage,
    })
  }

  report({ status: 'downloading', loaded: 0, total: 4252272, percent: 5 })

  // Strategy 1: Fetch via Stream / Blob (Works best inside sandboxed iframes & web embeds)
  for (const targetUrl of fallbackUrls) {
    try {
      const response = await fetch(targetUrl, {
        headers: {
          Accept: 'application/octet-stream, application/vnd.microsoft.portable-executable, */*',
        },
      })

      if (!response.ok) {
        continue
      }

      const contentLength = response.headers.get('content-length')
      const total = contentLength ? parseInt(contentLength, 10) : 4252272

      if (!response.body) {
        // Fallback to simple blob
        const blob = await response.blob()
        const objectUrl = window.URL.createObjectURL(blob)
        triggerDownload(objectUrl, filename)
        setTimeout(() => window.URL.revokeObjectURL(objectUrl), 60000)
        report({ status: 'completed', loaded: blob.size, total: blob.size, percent: 100 })
        return true
      }

      // Stream with real progress tracking
      const reader = response.body.getReader()
      const chunks: Uint8Array[] = []
      let receivedBytes = 0

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        if (value) {
          chunks.push(value)
          receivedBytes += value.length
          const percent = total > 0 ? Math.min(99, Math.round((receivedBytes / total) * 100)) : 50
          report({ status: 'downloading', loaded: receivedBytes, total, percent })
        }
      }

      const blob = new Blob(chunks, { type: 'application/octet-stream' })
      const objectUrl = window.URL.createObjectURL(blob)
      triggerDownload(objectUrl, filename)
      setTimeout(() => window.URL.revokeObjectURL(objectUrl), 60000)
      report({ status: 'completed', loaded: receivedBytes, total: receivedBytes, percent: 100 })
      return true
    } catch (err: any) {
      console.warn(`[HSBot Downloader] Strategy 1 failed for ${targetUrl}:`, err)
    }
  }

  // Strategy 2: Direct Anchor Click Fallback
  try {
    const a = document.createElement('a')
    a.href = primaryUrl
    a.download = filename
    a.target = '_blank'
    a.rel = 'noopener noreferrer'
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    report({ status: 'completed', loaded: 4252272, total: 4252272, percent: 100 })
    return true
  } catch (err: any) {
    console.error('[HSBot Downloader] Strategy 2 failed:', err)
  }

  // Strategy 3: Report Blocked / Manual Action Needed
  report({
    status: 'blocked',
    loaded: 0,
    total: 4252272,
    percent: 0,
    errorMessage: 'Direct download was blocked by your browser iframe permissions. Use direct link or copy URL.',
  })
  return false
}

function triggerDownload(url: string, filename: string) {
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.target = '_blank'
  link.rel = 'noopener noreferrer'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

export function triggerBrowserDownload(blob: Blob, filename: string) {
  const objectUrl = window.URL.createObjectURL(blob)
  triggerDownload(objectUrl, filename)
  setTimeout(() => {
    try {
      window.URL.revokeObjectURL(objectUrl)
    } catch {}
  }, 60000)
}
