import { useRef, useCallback, useState, useEffect } from 'react'
import { useVoiceActivityDetection } from './useVoiceActivityDetection'
import { useWakeWordDetection } from './useWakeWord'
import { useChat } from '@/stores/chat'
import { getBaseUrl, getAuthHeader } from '@/lib/api'
import { DEFAULT_VOICE_CONFIG, VoiceConfig, VoiceState, VOICE_STATES } from '@/lib/voice'

interface HandsFreeOptions {
  config?: Partial<VoiceConfig>
  onTranscript?: (text: string) => void
  onError?: (error: string) => void
}

interface HandsFreeState extends VoiceState {
  isHandsFree: boolean
  wakeWordDetected: boolean
  wsConnected: boolean
}

export function useHandsFreeVoice(options: HandsFreeOptions = {}) {
  const { config: userConfig, onTranscript, onError } = options
  const { sendMessage, currentChat, streaming } = useChat()

  const mergedConfig: VoiceConfig = {
    ...DEFAULT_VOICE_CONFIG,
    ...userConfig,
  }

  const [state, setState] = useState<HandsFreeState>({
    status: VOICE_STATES.IDLE,
    transcript: '',
    isRecording: false,
    audioLevel: 0,
    error: null,
    isHandsFree: false,
    wakeWordDetected: false,
    wsConnected: false,
  })

  const wsRef = useRef<WebSocket | null>(null)
  const audioQueueRef = useRef<HTMLAudioElement[]>([])
  const isPlayingRef = useRef(false)
  const currentAudioRef = useRef<HTMLAudioElement | null>(null)
  const mediaStreamRef = useRef<MediaStream | null>(null)
  const isInterruptedRef = useRef(false)
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Wake word detection
  const handleWakeWord = useCallback(() => {
    setState(prev => ({ ...prev, wakeWordDetected: true }))
    if (state.status === VOICE_STATES.IDLE || state.status === VOICE_STATES.LISTENING) {
      startListening()
    }
  }, [state.status])

  const { isListening: isWakeWordListening, startListening: startWakeWord, stopListening: stopWakeWord } = 
    useWakeWordDetection({
      wakeWord: mergedConfig.wakeWord,
      onWakeWord: handleWakeWord,
    })

  // Voice Activity Detection
  const handleSpeechStart = useCallback(() => {
    setState(prev => ({ ...prev, status: VOICE_STATES.SPEAKING }))
  }, [])

  const handleSpeechEnd = useCallback(async (audioBlob: Blob) => {
    setState(prev => ({ ...prev, status: VOICE_STATES.PROCESSING }))
    
    try {
      const text = await transcribeAudio(audioBlob, mergedConfig.language)
      setState(prev => ({ ...prev, transcript: text, status: VOICE_STATES.PROCESSING }))
      onTranscript?.(text)
      
      // Send to chat
      if (currentChat?.id) {
        await sendMessage(text, currentChat.id)
      }
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Transcription failed'
      setState(prev => ({ ...prev, error: errorMsg, status: VOICE_STATES.ERROR }))
      onError?.(errorMsg)
    }
  }, [mergedConfig.language, currentChat?.id, sendMessage, onTranscript, onError])

  const handleVolumeChange = useCallback((volume: number) => {
    setState(prev => ({ ...prev, audioLevel: volume }))
  }, [])

  const {
    isRecording,
    isSpeaking,
    audioLevel,
    startRecording,
    stopRecording,
  } = useVoiceActivityDetection({
    onSpeechStart: handleSpeechStart,
    onSpeechEnd: handleSpeechEnd,
    onVolumeChange: handleVolumeChange,
    silenceTimeout: mergedConfig.silenceTimeout,
    minSpeechDuration: mergedConfig.minSpeechDuration,
    maxRecordingDuration: mergedConfig.maxRecordingDuration,
  })

  // Transcribe audio using REST endpoint
  const transcribeAudio = async (audioBlob: Blob, language: string): Promise<string> => {
    const formData = new FormData()
    formData.append('file', audioBlob, 'audio.wav')
    formData.append('language', language)
    
    const response = await fetch(`${getBaseUrl()}/api/nvidia/speech/transcribe`, {
      method: 'POST',
      body: formData,
      headers: getAuthHeader(),
    })
    
    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || 'Transcription failed')
    }
    
    const data = await response.json()
    return data.text
  }

  // WebSocket connection for real-time voice
  const connectWebSocket = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return

    const wsUrl = getBaseUrl().replace('http://', 'ws://').replace('https://', 'wss://') + '/api/nvidia/speech/ws'
    const ws = new WebSocket(wsUrl)
    wsRef.current = ws

    ws.onopen = () => {
      setState(prev => ({ ...prev, wsConnected: true }))
      // Send initial config
      ws.send(JSON.stringify({
        type: 'start',
        language: mergedConfig.language,
        voice: mergedConfig.voice,
        sample_rate: mergedConfig.sampleRate,
        model: mergedConfig.model,
      }))
    }

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data)
        
        switch (msg.type) {
          case 'audio_chunk':
            // Play incoming TTS audio chunk
            playAudioChunk(msg.data)
            break
          case 'audio_end':
            handleAudioEnd()
            break
          case 'transcript':
            if (msg.text) {
              setState(prev => ({ ...prev, transcript: msg.text }))
              onTranscript?.(msg.text)
            }
            break
          case 'error':
            setState(prev => ({ ...prev, error: msg.content, status: VOICE_STATES.ERROR }))
            onError?.(msg.content)
            break
          case 'started':
            setState(prev => ({ ...prev, wsConnected: true }))
            break
          case 'configured':
            break
        }
      } catch (err) {
        console.error('WebSocket message error:', err)
      }
    }

    ws.onclose = () => {
      setState(prev => ({ ...prev, wsConnected: false }))
      // Attempt reconnect
      if (state.isHandsFree) {
        reconnectTimeoutRef.current = setTimeout(() => {
          connectWebSocket()
        }, 3000)
      }
    }

    ws.onerror = (err) => {
      console.error('WebSocket error:', err)
      setState(prev => ({ ...prev, wsConnected: false }))
    }
  }, [mergedConfig, state.isHandsFree, onTranscript, onError])

  const playAudioChunk = useCallback(async (base64Data: string) => {
    try {
      const binaryString = atob(base64Data)
      const bytes = new Uint8Array(binaryString.length)
      for (let i = 0; i < binaryString.length; i++) {
        bytes[i] = binaryString.charCodeAt(i)
      }
      
      const audioContext = new AudioContext({ sampleRate: mergedConfig.sampleRate })
      const audioBuffer = await audioContext.decodeAudioData(bytes.buffer)
      const source = audioContext.createBufferSource()
      source.buffer = audioBuffer
      source.connect(audioContext.destination)
      source.start(0)
      
      audioQueueRef.current.push(source as any)
    } catch (err) {
      console.error('Failed to play audio chunk:', err)
    }
  }, [mergedConfig.sampleRate])

  const handleAudioEnd = useCallback(() => {
    isPlayingRef.current = false
    setState(prev => ({ ...prev, status: VOICE_STATES.LISTENING }))
  }, [])

  // Interrupt AI speech
  const interrupt = useCallback(() => {
    isInterruptedRef.current = true
    isPlayingRef.current = false
    
    // Stop current audio
    if (currentAudioRef.current) {
      currentAudioRef.current.pause()
      currentAudioRef.current = null
    }
    
    // Clear audio queue
    audioQueueRef.current = []
    
    // Send interrupt via WebSocket
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'interrupt' }))
    }
    
    setState(prev => ({ ...prev, status: VOICE_STATES.LISTENING }))
    startListening()
  }, [])

  // Start listening for user speech
  const startListening = useCallback(() => {
    if (state.status === VOICE_STATES.AI_SPEAKING) {
      interrupt()
      return
    }
    
    if (!state.isRecording && state.status !== VOICE_STATES.PROCESSING) {
      startRecording()
    }
  }, [state.status, state.isRecording, startRecording, interrupt])

  // Stop listening
  const stopListening = useCallback(() => {
    stopRecording()
  }, [stopRecording])

  // Toggle hands-free mode
  const toggleHandsFree = useCallback(async (enabled: boolean) => {
    if (enabled) {
      try {
        // Request microphone permission
        const stream = await navigator.mediaDevices.getUserMedia({
          audio: {
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: true,
            sampleRate: 24000,
            channelCount: 1,
          },
        })
        mediaStreamRef.current = stream

        setState(prev => ({
          ...prev,
          isHandsFree: true,
          status: mergedConfig.wakeWordEnabled ? VOICE_STATES.IDLE : VOICE_STATES.LISTENING,
          error: null,
        }))

        connectWebSocket()

        if (mergedConfig.wakeWordEnabled) {
          startWakeWord()
        } else {
          startListening()
        }
      } catch (err) {
        const errorMsg = 'Microphone permission denied'
        setState(prev => ({ ...prev, error: errorMsg, isHandsFree: false }))
        onError?.(errorMsg)
      }
    } else {
      // Disable hands-free mode
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
      stopWakeWord()
      stopListening()
      stopRecording()
      
      if (wsRef.current) {
        wsRef.current.close()
        wsRef.current = null
      }

      if (mediaStreamRef.current) {
        mediaStreamRef.current.getTracks().forEach(track => track.stop())
        mediaStreamRef.current = null
      }

      // Stop any playing audio
      audioQueueRef.current.forEach(audio => {
        try { audio.pause() } catch {}
      })
      audioQueueRef.current = []

      setState(prev => ({
        ...prev,
        isHandsFree: false,
        status: VOICE_STATES.IDLE,
        transcript: '',
        wakeWordDetected: false,
        wsConnected: false,
      }))
    }
  }, [mergedConfig.wakeWordEnabled, connectWebSocket, startWakeWord, stopWakeWord, startListening, stopListening, stopRecording])

  // Send text for TTS via WebSocket
  const speakText = useCallback(async (text: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      setState(prev => ({ ...prev, status: VOICE_STATES.AI_SPEAKING }))
      wsRef.current.send(JSON.stringify({
        type: 'text',
        content: text,
      }))
    } else {
      // Fallback to REST API
      try {
        const audioBlob = await synthesizeSpeech(text, mergedConfig)
        playAudioBlob(audioBlob)
      } catch (err) {
        console.error('TTS fallback failed:', err)
      }
    }
  }, [mergedConfig])

  // Synthesize speech using REST endpoint
  const synthesizeSpeech = async (text: string, config: Partial<VoiceConfig> = {}): Promise<Blob> => {
    const response = await fetch(`${getBaseUrl()}/api/nvidia/speech/synthesize`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeader(),
      },
      body: JSON.stringify({
        text,
        voice: config.voice || mergedConfig.voice,
        model: config.model || mergedConfig.model,
        language: config.language || mergedConfig.language,
        sample_rate: config.sampleRate || mergedConfig.sampleRate,
      }),
    })
    
    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || 'Speech synthesis failed')
    }
    
    return response.blob()
  }

  const playAudioBlob = useCallback(async (blob: Blob) => {
    const url = URL.createObjectURL(blob)
    const audio = new Audio(url)
    currentAudioRef.current = audio
    isPlayingRef.current = true
    setState(prev => ({ ...prev, status: VOICE_STATES.AI_SPEAKING }))
    
    audio.onended = () => {
      isPlayingRef.current = false
      URL.revokeObjectURL(url)
      if (state.isHandsFree) {
        setState(prev => ({ ...prev, status: VOICE_STATES.LISTENING }))
        startListening()
      }
    }
    
    audio.onerror = () => {
      isPlayingRef.current = false
      URL.revokeObjectURL(url)
      if (state.isHandsFree) {
        setState(prev => ({ ...prev, status: VOICE_STATES.LISTENING }))
        startListening()
      }
    }
    
    await audio.play()
  }, [state.isHandsFree])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
      if (wsRef.current) {
        wsRef.current.close()
      }
      if (mediaStreamRef.current) {
        mediaStreamRef.current.getTracks().forEach(track => track.stop())
      }
      audioQueueRef.current.forEach(audio => {
        try { audio.pause() } catch {}
      })
    }
  }, [])

  return {
    ...state,
    isRecording,
    isSpeaking,
    audioLevel,
    isWakeWordListening,
    toggleHandsFree,
    startListening,
    stopListening,
    interrupt,
    speakText,
    connectWebSocket,
  }
}