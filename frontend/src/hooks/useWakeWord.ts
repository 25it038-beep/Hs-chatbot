import { useRef, useCallback, useState, useEffect } from 'react'

interface WakeWordOptions {
  wakeWord: string
  onWakeWord?: () => void
  sensitivity?: number
}

interface WakeWordState {
  isListening: boolean
  detected: boolean
}

// Extend Window interface for SpeechRecognition
declare global {
  interface Window {
    SpeechRecognition: any
    webkitSpeechRecognition: any
  }
}

export function useWakeWordDetection(options: WakeWordOptions = { wakeWord: 'hey hs' }) {
  const { wakeWord, onWakeWord, sensitivity = 0.5 } = options
  const [state, setState] = useState<WakeWordState>({
    isListening: false,
    detected: false,
  })

  const recognitionRef = useRef<any>(null)
  const isProcessingRef = useRef(false)

  const startListening = useCallback(() => {
    if (state.isListening) return

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
    if (!SpeechRecognition) {
      console.warn('Speech Recognition not supported in this browser')
      return
    }

    const recognition = new SpeechRecognition()
    recognition.continuous = true
    recognition.interimResults = true
    recognition.lang = 'en-US'
    recognition.maxAlternatives = 1

    recognition.onresult = (event: any) => {
      if (isProcessingRef.current) return

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i]
        if (result.isFinal) {
          const transcript = result[0].transcript.toLowerCase().trim()
          if (transcript.includes(wakeWord.toLowerCase())) {
            isProcessingRef.current = true
            setState(prev => ({ ...prev, detected: true }))
            onWakeWord?.()
            
            setTimeout(() => {
              setState(prev => ({ ...prev, detected: false }))
              isProcessingRef.current = false
            }, 1000)
            break
          }
        }
      }
    }

    recognition.onerror = (event: any) => {
      if (event.error !== 'no-speech') {
        console.warn('Wake word recognition error:', event.error)
      }
    }

    recognition.onend = () => {
      if (state.isListening) {
        setTimeout(() => {
          if (state.isListening) {
            recognition.start()
          }
        }, 100)
      }
    }

    recognitionRef.current = recognition
    setState(prev => ({ ...prev, isListening: true }))
    recognition.start()
  }, [wakeWord, state.isListening, onWakeWord])

  const stopListening = useCallback(() => {
    if (recognitionRef.current) {
      recognitionRef.current.stop()
      recognitionRef.current = null
    }
    setState(prev => ({ ...prev, isListening: false, detected: false }))
    isProcessingRef.current = false
  }, [state.isListening])

  useEffect(() => {
    return () => {
      stopListening()
    }
  }, [stopListening])

  return {
    ...state,
    startListening,
    stopListening,
  }
}

// Porcupine wake word detection (optional, requires @picovoice/porcupine-web)
// This is a best-effort implementation that works with the Porcupine Web API
export function usePorcupineWakeWord(
  accessKey: string,
  keywords: string[] = ['hey hs'],
  onDetection: (keyword: string) => void
) {
  const [isLoaded, setIsLoaded] = useState(false)
  const [isListening, setIsListening] = useState(false)
  const porcupineRef = useRef<any>(null)
  const audioContextRef = useRef<AudioContext | null>(null)
  const processorRef = useRef<any>(null)

  const initPorcupine = useCallback(async () => {
    try {
      // Dynamic import for Porcupine Web
      const mod = await import('@picovoice/porcupine-web')
      const { PorcupineWorker, BuiltInKeyword } = mod
      
      // Convert keyword strings to BuiltInKeyword
      const keywordConfigs = keywords.map(kw => ({
        builtin: kw as any,
        sensitivity: 0.5,
      }))
      
      // PorcupineWorker.create expects: accessKey, keywords, keywordDetectionCallback, model, options?
      const porcupine = await PorcupineWorker.create(
        accessKey,
        keywordConfigs,
        (detection: any) => {
          // detection is PorcupineDetection with index and label
          const keyword = detection?.label || keywords[detection?.index] || 'unknown'
          onDetection(keyword)
        },
        {}, // empty model - will use default
        { device: 'best' }
      )
      porcupineRef.current = porcupine
      
      setIsLoaded(true)
    } catch (error) {
      console.error('Failed to initialize Porcupine:', error)
    }
  }, [accessKey, keywords])

  const startListening = useCallback(async () => {
    if (!isLoaded || !porcupineRef.current) return

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: porcupineRef.current.sampleRate,
          channelCount: 1,
        },
      })

      audioContextRef.current = new AudioContext({ sampleRate: porcupineRef.current.sampleRate })
      const source = audioContextRef.current.createMediaStreamSource(stream)
      
      try {
        await audioContextRef.current.audioWorklet.addModule('/porcupine-processor.js')
        processorRef.current = new AudioWorkletNode(audioContextRef.current, 'porcupine-processor')
        
        source.connect(processorRef.current)
        processorRef.current.connect(audioContextRef.current.destination)
        
        processorRef.current.port.onmessage = (event: MessageEvent) => {
          if (event.data?.command === 'process') {
            porcupineRef.current.process(event.data.audioFrame)
          }
        }
      } catch (workletError) {
        console.warn('AudioWorklet not available, using fallback processing')
        // Fallback: use ScriptProcessorNode (deprecated but works)
        const processor = audioContextRef.current.createScriptProcessor(512, 1, 1)
        processor.onaudioprocess = (e) => {
          const inputData = e.inputBuffer.getChannelData(0)
          porcupineRef.current.process(inputData)
        }
        source.connect(processor)
        processor.connect(audioContextRef.current.destination)
        processorRef.current = processor
      }
      
      setIsListening(true)
    } catch (error) {
      console.error('Failed to start wake word listening:', error)
    }
  }, [isLoaded])

  const stopListening = useCallback(() => {
    if (processorRef.current) {
      processorRef.current.disconnect()
      processorRef.current = null
    }
    if (audioContextRef.current) {
      audioContextRef.current.close()
      audioContextRef.current = null
    }
    setIsListening(false)
  }, [])

  useEffect(() => {
    return () => {
      stopListening()
      if (porcupineRef.current) {
        porcupineRef.current.release?.()
        porcupineRef.current = null
      }
    }
  }, [stopListening])

  return {
    isLoaded,
    isListening,
    initPorcupine,
    startListening,
    stopListening,
  }
}