import { useRef, useCallback, useState, useEffect } from 'react'

interface VADOptions {
  onSpeechStart?: () => void
  onSpeechEnd?: (audioBlob: Blob) => void
  onVolumeChange?: (volume: number) => void
  silenceTimeout?: number
  minSpeechDuration?: number
  maxRecordingDuration?: number
  noiseThreshold?: number
}

interface VADState {
  isRecording: boolean
  isSpeaking: boolean
  audioLevel: number
  recordingDuration: number
}

export function useVoiceActivityDetection(options: VADOptions = {}) {
  const {
    onSpeechStart,
    onSpeechEnd,
    onVolumeChange,
    silenceTimeout = 1500,
    minSpeechDuration = 500,
    maxRecordingDuration = 30000,
    noiseThreshold = 0.01,
  } = options

  const [state, setState] = useState<VADState>({
    isRecording: false,
    isSpeaking: false,
    audioLevel: 0,
    recordingDuration: 0,
  })

  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const audioContextRef = useRef<AudioContext | null>(null)
  const analyserRef = useRef<AnalyserNode | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const silenceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const recordingStartRef = useRef<number>(0)
  const animationFrameRef = useRef<number>(0)
  const speechStartedRef = useRef(false)

  const stopRecording = useCallback(() => {
    if (silenceTimerRef.current) {
      clearTimeout(silenceTimerRef.current)
      silenceTimerRef.current = null
    }
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current)
      animationFrameRef.current = 0
    }
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop()
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop())
      streamRef.current = null
    }
    if (audioContextRef.current) {
      audioContextRef.current.close()
      audioContextRef.current = null
    }
  }, [])

  const processAudioData = useCallback((event: BlobEvent) => {
    if (event.data.size > 0) {
      chunksRef.current.push(event.data)
    }
  }, [])

  const checkVolume = useCallback(() => {
    if (!analyserRef.current || !state.isRecording) return

    const dataArray = new Uint8Array(analyserRef.current.frequencyBinCount)
    analyserRef.current.getByteFrequencyData(dataArray)
    
    const average = dataArray.reduce((a, b) => a + b, 0) / dataArray.length
    const volume = average / 255

    setState(prev => ({ ...prev, audioLevel: volume }))
    onVolumeChange?.(volume)

    const isSpeech = volume > noiseThreshold
    const now = Date.now()
    const recordingDuration = now - recordingStartRef.current

    if (isSpeech && !speechStartedRef.current) {
      speechStartedRef.current = true
      setState(prev => ({ ...prev, isSpeaking: true }))
      onSpeechStart?.()
    }

    if (speechStartedRef.current) {
      if (!isSpeech) {
        if (silenceTimerRef.current) {
          clearTimeout(silenceTimerRef.current)
        }
        silenceTimerRef.current = setTimeout(() => {
          if (recordingDuration >= minSpeechDuration) {
            stopRecording()
            const audioBlob = new Blob(chunksRef.current, { type: 'audio/wav' })
            onSpeechEnd?.(audioBlob)
          } else {
            speechStartedRef.current = false
            setState(prev => ({ ...prev, isSpeaking: false }))
            chunksRef.current = []
            recordingStartRef.current = Date.now()
          }
        }, silenceTimeout)
      } else {
        if (silenceTimerRef.current) {
          clearTimeout(silenceTimerRef.current)
          silenceTimerRef.current = null
        }
      }
    }

    if (recordingDuration >= maxRecordingDuration) {
      stopRecording()
      const audioBlob = new Blob(chunksRef.current, { type: 'audio/wav' })
      onSpeechEnd?.(audioBlob)
      return
    }

    if (state.isRecording) {
      animationFrameRef.current = requestAnimationFrame(checkVolume)
    }
  }, [
    state.isRecording,
    noiseThreshold,
    silenceTimeout,
    minSpeechDuration,
    maxRecordingDuration,
    onSpeechStart,
    onSpeechEnd,
    onVolumeChange,
    stopRecording,
  ])

  const startRecording = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          sampleRate: 24000,
          channelCount: 1,
        },
      })

      streamRef.current = stream
      chunksRef.current = []
      speechStartedRef.current = false
      recordingStartRef.current = Date.now()

      const audioContext = new AudioContext({ sampleRate: 24000 })
      audioContextRef.current = audioContext

      const analyser = audioContext.createAnalyser()
      analyser.fftSize = 256
      analyser.smoothingTimeConstant = 0.8
      analyserRef.current = analyser

      const source = audioContext.createMediaStreamSource(stream)
      source.connect(analyser)

      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: 'audio/wav',
      })
      mediaRecorderRef.current = mediaRecorder
      mediaRecorder.ondataavailable = processAudioData

      mediaRecorder.start(100)

      setState({
        isRecording: true,
        isSpeaking: false,
        audioLevel: 0,
        recordingDuration: 0,
      })

      animationFrameRef.current = requestAnimationFrame(checkVolume)
    } catch (error) {
      console.error('Failed to start recording:', error)
      throw error
    }
  }, [checkVolume, processAudioData])

  const stop = useCallback(() => {
    stopRecording()
    setState(prev => ({
      ...prev,
      isRecording: false,
      isSpeaking: false,
      recordingDuration: Date.now() - recordingStartRef.current,
    }))
    speechStartedRef.current = false
  }, [stopRecording])

  useEffect(() => {
    let interval: ReturnType<typeof setInterval>
    if (state.isRecording) {
      interval = setInterval(() => {
        setState(prev => ({
          ...prev,
          recordingDuration: Date.now() - recordingStartRef.current,
        }))
      }, 100)
    }
    return () => {
      if (interval) clearInterval(interval)
    }
  }, [state.isRecording])

  useEffect(() => {
    return () => {
      stopRecording()
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current)
      }
    }
  }, [stopRecording])

  return {
    ...state,
    startRecording,
    stopRecording: stop,
  }
}