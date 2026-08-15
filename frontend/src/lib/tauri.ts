// Desktop overlay helpers — safe no-ops in the plain web build (§1-4, §13-17).
// Every function guards on `isTauri`, so the web app never touches Tauri APIs.

export const isTauri =
  typeof window !== 'undefined' &&
  ('__TAURI_INTERNALS__' in window || '__TAURI__' in window)

type LogicalSize = { width: number; height: number }

export const COMPACT_SIZE: LogicalSize = { width: 380, height: 620 }
export const EXPANDED_SIZE: LogicalSize = { width: 460, height: 760 }

async function withWindow<T>(fn: (w: any) => Promise<T>): Promise<T | null> {
  if (!isTauri) return null
  try {
    const { getCurrentWindow } = await import('@tauri-apps/api/window')
    return await fn(getCurrentWindow())
  } catch {
    return null
  }
}

export function hideWindow(): Promise<null | void> {
  return withWindow(w => w.hide())
}

export function minimizeWindow(): Promise<null | void> {
  return withWindow(w => w.minimize())
}

export function toggleAlwaysOnTop(on: boolean): Promise<null | void> {
  return withWindow(w => w.setAlwaysOnTop(on))
}

export function setWindowSize(size: LogicalSize): Promise<null | void> {
  return withWindow(async w => {
    const { LogicalSize } = await import('@tauri-apps/api/dpi')
    await w.setSize(new LogicalSize(size.width, size.height))
  })
}

export function focusWindow(): Promise<null | void> {
  return withWindow(w => w.unminimize().then(() => w.setFocus()))
}

/** Global-hotkey bridge: when the desktop shell emits "hsai:focus"
 * (Rust-side Ctrl+Space registration), bring the input to front. */
export function listenForHotkeyFocus(onFocus: () => void): () => void {
  if (!isTauri) return () => {}
  let unlisten: (() => void) | undefined
  import('@tauri-apps/api/event')
    .then(({ listen }) =>
      listen('hsai:focus', () => {
        onFocus()
      }).then(fn => {
        unlisten = fn
      }),
    )
    .catch(() => {})
  return () => unlisten?.()
}

/** Desktop notification (Windows toast). Only fires when the window is
 * hidden/minimized so we never annoy the user while the chat is visible. */
export function notify(title: string, body: string): void {
  if (!isTauri || !document.hidden) return
  import('@tauri-apps/plugin-notification')
    .then(({ isPermissionGranted, requestPermission, sendNotification }) =>
      isPermissionGranted().then(granted => {
        if (granted) return 'granted' as const
        return requestPermission()
      }).then(status => {
        if (status === 'granted') sendNotification({ title, body })
      }),
    )
    .catch(() => {})
}
