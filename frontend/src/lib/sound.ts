let audioCtx: AudioContext | null = null

function getAudioContext(): AudioContext | null {
  if (typeof window === 'undefined') return null
  try {
    if (!audioCtx) {
      const Ctor = window.AudioContext || (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext
      if (!Ctor) return null
      audioCtx = new Ctor()
    }
    if (audioCtx.state === 'suspended') {
      audioCtx.resume().catch(() => {})
    }
    return audioCtx
  } catch {
    return null
  }
}

function tone(
  ctx: AudioContext,
  dest: AudioNode,
  frequency: number,
  startAt: number,
  duration: number,
  volume: number,
) {
  const osc = ctx.createOscillator()
  const gain = ctx.createGain()
  osc.type = 'sine'
  osc.frequency.value = frequency
  gain.gain.setValueAtTime(0.0001, startAt)
  gain.gain.exponentialRampToValueAtTime(volume, startAt + 0.02)
  gain.gain.exponentialRampToValueAtTime(0.0001, startAt + duration)
  osc.connect(gain)
  gain.connect(dest)
  osc.start(startAt)
  osc.stop(startAt + duration + 0.05)
}

export function playCompletionSound() {
  const ctx = getAudioContext()
  if (!ctx) return
  try {
    const master = ctx.createGain()
    master.gain.value = 0.25
    master.connect(ctx.destination)
    const now = ctx.currentTime
    tone(ctx, master, 659.25, now + 0.05, 0.22, 0.9)
    tone(ctx, master, 987.77, now + 0.18, 0.35, 0.9)
  } catch {
    // ignore audio errors
  }
}
