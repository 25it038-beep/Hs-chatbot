import type { Plugin } from 'vite'
import { WebSocketServer, WebSocket } from 'ws'
import { nvidiaLiveService } from './nvidiaLiveService'

export function liveApiPlugin(): Plugin {
  // In-memory chat storage for seamless normal text chat
  const inMemoryChats: Record<string, any> = {}
  const inMemoryMessages: Record<string, any[]> = {}
  const liveSessionHistories: Record<string, { role: string; content: string }[]> = {}

  return {
    name: 'hsbot-live-api-plugin',
    configureServer(server) {
      // 1. Setup WebSocket server on Vite HTTP server
      if (server.httpServer) {
        const wss = new WebSocketServer({ noServer: true })

        server.httpServer.on('upgrade', (req, socket, head) => {
          const url = new URL(req.url || '', `http://${req.headers.host}`)
          if (url.pathname.startsWith('/api/live/ws')) {
            wss.handleUpgrade(req, socket, head, (ws) => {
              wss.emit('connection', ws, req)
            })
          }
        })

        wss.on('connection', (ws: WebSocket, req) => {
          const url = new URL(req.url || '', `http://${req.headers.host}`)
          const sessionId = url.pathname.replace('/api/live/ws/', '').replace('/api/live/ws', '') || url.searchParams.get('sessionId') || 'session_default'
          console.log(`[LiveApiPlugin] Client connected to live session: ${sessionId}`)

          let audioChunks: Buffer[] = []
          let lastVoiceTime = 0
          let hasVoiceInTurn = false
          let isProcessing = false
          let isInterrupted = false
          let silenceInterval: any = null
          let abortController: AbortController | null = null
          const conversationHistory: { role: string; content: string }[] = []

          function analyzePcmChunk(chunk: Buffer) {
            let sumSquares = 0
            let peak = 0
            const sampleCount = Math.floor(chunk.length / 2)
            for (let i = 0; i < chunk.length - 1; i += 2) {
              const s = chunk.readInt16LE(i)
              const abs = Math.abs(s)
              if (abs > peak) peak = abs
              sumSquares += (s / 32768) * (s / 32768)
            }
            const rms = Math.sqrt(sumSquares / (sampleCount || 1))
            return { rms, peak }
          }

          // Common turn execution pipeline
          const runTurnPipeline = async (userText: string) => {
            try {
              // 1. Send User Transcript
              ws.send(JSON.stringify({
                type: 'transcript',
                role: 'user',
                text: userText,
                isFinal: true,
              }))
              conversationHistory.push({ role: 'user', content: userText })

              // 2. Stream LLM with NVIDIA NIM
              abortController = new AbortController()
              const messages = [
                {
                  role: 'system',
                  content:
                    'You are HSBot, a helpful, natural conversational voice assistant powered by NVIDIA NIM. ' +
                    'Keep your answers concise, clear, and direct (1 to 2 spoken sentences). ' +
                    'Never use markdown, bullet points, asterisks, or emojis, as your response will be spoken aloud.',
                },
                ...conversationHistory.slice(-6),
              ]

              const tAsrFinal = Date.now()
              let tLlmFirst = 0
              let firstAudioSent = false

              ws.send(JSON.stringify({ type: 'status', state: 'PROCESSING', message: 'Thinking (NVIDIA NIM)...' }))
              const llmRes = await nvidiaLiveService.chatCompletion(messages, true)
              let fullReply = ''
              let sentenceBuffer = ''
              let chunkIndex = 0

              // Async queue for TTS phrases
              const phraseQueue: string[] = []
              let isSynthesizing = false
              let ttsResolve: (() => void) | null = null

              const processTtsQueue = async () => {
                if (isSynthesizing) return
                isSynthesizing = true

                while (phraseQueue.length > 0) {
                  if (isInterrupted) break
                  const phrase = phraseQueue.shift()!
                  const clean = phrase.replace(/[*_#`~[\]]/g, '').trim()
                  if (clean.length < 2) continue

                  try {
                    await nvidiaLiveService.streamSynthesizePCM(
                      clean,
                      'Chatterbox-Multilingual',
                      24000,
                      (audioBase64) => {
                        if (isInterrupted) return
                        if (!firstAudioSent) {
                          firstAudioSent = true
                          const tFirstAudio = Date.now()
                          const llmToTts = tLlmFirst ? tFirstAudio - tLlmFirst : 0
                          const totalLat = tFirstAudio - tAsrFinal

                          console.log(`[LIVE][TIMING] LLM_FIRST_TOKEN → TTS_FIRST_AUDIO = ${llmToTts} ms`)
                          console.log(`[LIVE][TIMING] ASR_FINAL → SPEAKER = ${totalLat} ms`)

                          ws.send(JSON.stringify({ type: 'status', state: 'SPEAKING', message: 'Speaking...' }))
                          ws.send(JSON.stringify({ type: 'timing', metric: 'llm_first_token_to_tts_first_audio_ms', value: llmToTts }))
                          ws.send(JSON.stringify({ type: 'timing', metric: 'total_latency_ms', value: totalLat }))
                        }

                        ws.send(JSON.stringify({
                          type: 'audio_chunk',
                          audio: audioBase64,
                          sampleRate: 24000,
                          index: chunkIndex++,
                        }))
                      }
                    )
                  } catch (ttsErr: any) {
                    console.warn('[LiveApiPlugin] Sentence TTS error:', ttsErr?.message)
                  }
                }

                isSynthesizing = false
                if (ttsResolve && phraseQueue.length === 0) {
                  ttsResolve()
                }
              }

              const enqueuePhrase = (phrase: string) => {
                phraseQueue.push(phrase)
                processTtsQueue()
              }

              if (llmRes.body) {
                const decoder = new TextDecoder()
                let buffer = ''
                // @ts-ignore
                for await (const chunk of llmRes.body) {
                  if (isInterrupted) break
                  buffer += typeof chunk === 'string' ? chunk : decoder.decode(chunk, { stream: true })
                  const lines = buffer.split('\n')
                  buffer = lines.pop() || ''
                  for (const line of lines) {
                    const trimmed = line.trim()
                    if (trimmed.startsWith('data: ') && !trimmed.includes('[DONE]')) {
                      try {
                        const parsed = JSON.parse(trimmed.substring(6))
                        const delta = parsed.choices?.[0]?.delta?.content || ''
                        if (delta) {
                          if (!tLlmFirst) {
                            tLlmFirst = Date.now()
                            const asrToLlm = tLlmFirst - tAsrFinal
                            console.log(`[LIVE][TIMING] ASR_FINAL → LLM_FIRST_TOKEN = ${asrToLlm} ms`)
                            ws.send(JSON.stringify({ type: 'timing', metric: 'asr_to_llm_first_token_ms', value: asrToLlm }))
                          }

                          fullReply += delta
                          sentenceBuffer += delta
                          ws.send(JSON.stringify({ type: 'llm_chunk', text: delta }))

                          // If sentence completed, enqueue immediately WITHOUT blocking LLM token reception
                          const match = sentenceBuffer.match(/^(.*?[.!?\n])\s*(.*)$/s)
                          if (match) {
                            const readySentence = match[1].trim()
                            sentenceBuffer = match[2] || ''
                            if (readySentence.length >= 3) {
                              enqueuePhrase(readySentence)
                            }
                          }
                        }
                      } catch {
                        // ignore json parse error
                      }
                    }
                  }
                }
              }

              // Enqueue remaining sentence buffer
              if (sentenceBuffer.trim().length > 0 && !isInterrupted) {
                enqueuePhrase(sentenceBuffer.trim())
              }

              // Await remaining TTS synthesis
              if (isSynthesizing || phraseQueue.length > 0) {
                await new Promise<void>((resolve) => {
                  ttsResolve = resolve
                  setTimeout(resolve, 8000) // safety timeout
                })
              }

              const finalReply = fullReply.trim() || 'I am here and listening.'
              if (!isInterrupted) {
                ws.send(JSON.stringify({
                  type: 'transcript',
                  role: 'assistant',
                  text: finalReply,
                  isFinal: true,
                }))
                conversationHistory.push({ role: 'assistant', content: finalReply })
              }
            } catch (err: any) {
              console.error('[LiveApiPlugin] Processing pipeline error:', err)
              ws.send(JSON.stringify({ type: 'error', code: 'PIPELINE_ERROR', message: err?.message || 'Error' }))
            } finally {
              isProcessing = false
              abortController = null
              ws.send(JSON.stringify({ type: 'status', state: 'LISTENING', message: 'Listening...' }))
            }
          }

          const processAudioBuffer = async (buffer: Buffer) => {
            if (isProcessing || buffer.length < 2400) return
            isProcessing = true
            isInterrupted = false

            try {
              ws.send(JSON.stringify({ type: 'status', state: 'PROCESSING', message: 'Transcribing speech...' }))
              const transcript = await nvidiaLiveService.transcribePCM(buffer, 'en-US')
              if (!transcript || transcript.trim().length === 0 || isInterrupted) {
                isProcessing = false
                ws.send(JSON.stringify({ type: 'status', state: 'LISTENING', message: 'Listening...' }))
                return
              }
              await runTurnPipeline(transcript.trim())
            } catch (err: any) {
              console.warn('[LiveApiPlugin] Audio transcription error:', err?.message)
              isProcessing = false
              ws.send(JSON.stringify({ type: 'status', state: 'LISTENING', message: 'Listening...' }))
            }
          }

          // Inform client of listening status
          ws.send(JSON.stringify({ type: 'status', state: 'LISTENING', message: 'Connected to NVIDIA NIM' }))

          const executeTurn = async (userText: string) => {
            if (isProcessing) return
            isProcessing = true
            isInterrupted = false
            await runTurnPipeline(userText)
          }

          let userSilenceTimeout = 1500

          // Voice turn silence detector loop (every 100ms)
          silenceInterval = setInterval(async () => {
            if (isProcessing || !hasVoiceInTurn) return

            const silenceDuration = Date.now() - lastVoiceTime
            const totalBytes = audioChunks.reduce((acc, c) => acc + c.length, 0)

            // If user spoke and has now been silent for userSilenceTimeout with sufficient audio recorded
            if (silenceDuration >= userSilenceTimeout && totalBytes >= 9600) {
              hasVoiceInTurn = false
              const fullBuffer = Buffer.concat(audioChunks)
              audioChunks = []
              await processAudioBuffer(fullBuffer)
            }
          }, 100)

          ws.on('message', async (raw: any) => {
            try {
              const msg = JSON.parse(raw.toString())
              if (msg.type === 'config' && msg.config?.silenceTimeoutMs) {
                userSilenceTimeout = Math.max(600, Math.min(5000, Number(msg.config.silenceTimeoutMs)))
              } else if (msg.type === 'ping') {
                ws.send(JSON.stringify({ type: 'pong', timestamp: msg.timestamp || Date.now() }))
              } else if (msg.type === 'user_speech') {
                const text = (msg.text || '').trim()
                if (text && !isProcessing) {
                  audioChunks = []
                  hasVoiceInTurn = false
                  await executeTurn(text)
                }
              } else if (msg.type === 'commit_turn') {
                if (!isProcessing && audioChunks.length > 0) {
                  hasVoiceInTurn = false
                  const fullBuffer = Buffer.concat(audioChunks)
                  audioChunks = []
                  await processAudioBuffer(fullBuffer)
                }
              } else if (msg.type === 'interrupt') {
                isInterrupted = true
                hasVoiceInTurn = false
                audioChunks = []
                if (abortController) {
                  abortController.abort()
                }
                ws.send(JSON.stringify({ type: 'status', state: 'LISTENING', message: 'Interrupted by user' }))
              } else if (msg.type === 'audio') {
                const b64 = msg.data
                if (b64 && !isProcessing) {
                  const chunk = Buffer.from(b64, 'base64')
                  const { rms, peak } = analyzePcmChunk(chunk)

                  // Sensitive voice detection threshold: normal human voice produces peak > 250 or rms > 0.003
                  const isVoice = peak > 250 || rms > 0.003

                  if (isVoice) {
                    if (!hasVoiceInTurn) {
                      hasVoiceInTurn = true
                      ws.send(JSON.stringify({ type: 'status', state: 'USER_SPEAKING', message: 'Hearing your voice...' }))
                    }
                    lastVoiceTime = Date.now()
                    audioChunks.push(chunk)
                  } else if (hasVoiceInTurn) {
                    // Collect post-speech trailing buffer so words aren't clipped
                    audioChunks.push(chunk)
                  } else {
                    // Pre-speech rolling buffer (keep up to ~0.4s = 12800 bytes)
                    audioChunks.push(chunk)
                    const totalBytes = audioChunks.reduce((acc, c) => acc + c.length, 0)
                    if (totalBytes > 12800) {
                      audioChunks.shift()
                    }
                  }
                }
              }
            } catch (err) {
              console.error('[LiveApiPlugin] Message error:', err)
            }
          })

          ws.on('close', () => {
            if (silenceInterval) clearInterval(silenceInterval)
            if (abortController) abortController.abort()
            console.log(`[LiveApiPlugin] Client disconnected from live session: ${sessionId}`)
          })
        })
      }

      // 2. HTTP Middlewares for live and regular API routes
      server.middlewares.use(async (req, res, next) => {
        const url = new URL(req.url || '', `http://${req.headers.host}`)
        const pathname = url.pathname

        if (!pathname.startsWith('/api/')) {
          return next()
        }

        const parseJsonBody = (): Promise<any> => {
          return new Promise((resolve) => {
            let data = ''
            req.on('data', (chunk) => {
              data += chunk
            })
            req.on('end', () => {
              try {
                resolve(JSON.parse(data || '{}'))
              } catch {
                resolve({})
              }
            })
          })
        }

        const parseBinaryBody = (): Promise<Buffer> => {
          return new Promise((resolve) => {
            const chunks: Buffer[] = []
            req.on('data', (chunk) => chunks.push(Buffer.from(chunk)))
            req.on('end', () => resolve(Buffer.concat(chunks)))
          })
        }

        try {
          // Health checks
          if (pathname === '/api/health' || pathname === '/api/live/health') {
            res.setHeader('Content-Type', 'application/json')
            res.end(
              JSON.stringify({
                status: 'ok',
                version: '1.0.0',
                subsystem: 'live_voice',
                provider: 'nvidia',
                asr: 'parakeet-tdt-0.6b-en-US-asr-offline',
                tts: 'chatterbox-multilingual',
                llm: 'meta/llama-3.2-11b-vision-instruct',
              })
            )
            return
          }

          // Live Voices
          if (pathname === '/api/live/voices') {
            res.setHeader('Content-Type', 'application/json')
            res.end(
              JSON.stringify({
                voices: [
                  { id: 'Chatterbox-Multilingual', name: 'Chatterbox Multilingual', language: 'en-US', default: true },
                  { id: 'English-US.Female-1', name: 'English US (Female)', language: 'en-US', default: false },
                  { id: 'English-US.Male-1', name: 'English US (Male)', language: 'en-US', default: false },
                ],
              })
            )
            return
          }

          // Models list
          if (pathname === '/api/models' || pathname === '/api/models/nvidia') {
            res.setHeader('Content-Type', 'application/json')
            res.end(
              JSON.stringify({
                models: [
                  { id: 'meta/llama-3.2-11b-vision-instruct', name: 'Llama 3.2 11B Vision (Fast)' },
                  { id: 'meta/llama-3.1-70b-instruct', name: 'Llama 3.1 70B Instruct' },
                  { id: 'mistralai/mistral-large-2-instruct', name: 'Mistral Large 2' },
                ],
              })
            )
            return
          }

          // Live ASR (Parakeet)
          if (pathname === '/api/live/transcribe' && req.method === 'POST') {
            const pcmBuffer = await parseBinaryBody()
            const transcript = await nvidiaLiveService.transcribePCM(pcmBuffer, 'en-US')
            res.setHeader('Content-Type', 'application/json')
            res.end(JSON.stringify({ transcript }))
            return
          }

          // Live LLM
          if (pathname === '/api/live/chat' && req.method === 'POST') {
            const body = await parseJsonBody()
            const messages = body.messages || []
            const stream = body.stream !== false
            const llmRes = await nvidiaLiveService.chatCompletion(messages, stream)

            if (stream) {
              res.setHeader('Content-Type', 'text/event-stream')
              res.setHeader('Cache-Control', 'no-cache')
              res.setHeader('Connection', 'keep-alive')
              if (llmRes.body) {
                // @ts-ignore
                for await (const chunk of llmRes.body) {
                  res.write(chunk)
                }
                res.end()
              } else {
                res.end('data: [DONE]\n\n')
              }
            } else {
              const data = await llmRes.json()
              res.setHeader('Content-Type', 'application/json')
              res.end(JSON.stringify(data))
            }
            return
          }

          // Live TTS (Chatterbox)
          if (pathname === '/api/live/synthesize' && req.method === 'POST') {
            const body = await parseJsonBody()
            const wavBuffer = await nvidiaLiveService.synthesizeSpeech(
              body.text,
              body.voiceName || 'Chatterbox-Multilingual',
              24000
            )
            res.setHeader('Content-Type', 'audio/wav')
            res.setHeader('Content-Length', wavBuffer.length)
            res.end(wavBuffer)
            return
          }

          // Live Session Connect (HTTP handshake fallback)
          if ((pathname === '/api/live/session/connect' || pathname === '/api/live/connect') && req.method === 'POST') {
            const body = await parseJsonBody()
            const sessionId = body.sessionId || 'session_' + Date.now()
            if (!liveSessionHistories[sessionId]) {
              liveSessionHistories[sessionId] = []
            }
            res.setHeader('Content-Type', 'application/json')
            res.end(
              JSON.stringify({
                status: 'ok',
                sessionId,
                state: 'LISTENING',
                message: 'Connected to NVIDIA NIM',
              })
            )
            return
          }

          // Live Turn SSE (Full bidirectional streaming turn over HTTP)
          if (pathname === '/api/live/turn' && req.method === 'POST') {
            const body = await parseJsonBody()
            const sessionId = body.sessionId || 'session_default'
            if (!liveSessionHistories[sessionId]) {
              liveSessionHistories[sessionId] = []
            }
            const history = liveSessionHistories[sessionId]

            res.setHeader('Content-Type', 'text/event-stream')
            res.setHeader('Cache-Control', 'no-cache')
            res.setHeader('Connection', 'keep-alive')

            const sendSSE = (obj: any) => {
              res.write(`data: ${JSON.stringify(obj)}\n\n`)
            }

            try {
              let userText = (body.text || '').trim()

              // If client sent audio chunks
              if (!userText && body.audioChunks && Array.isArray(body.audioChunks) && body.audioChunks.length > 0) {
                sendSSE({ type: 'status', state: 'PROCESSING', message: 'Transcribing speech...' })
                const pcmBuffers = body.audioChunks.map((b64: string) => Buffer.from(b64, 'base64'))
                const fullAudio = Buffer.concat(pcmBuffers)
                if (fullAudio.length >= 3200) {
                  const transcript = await nvidiaLiveService.transcribePCM(fullAudio, 'en-US')
                  userText = (transcript || '').trim()
                }
              }

              if (!userText) {
                sendSSE({ type: 'status', state: 'LISTENING', message: 'Listening...' })
                res.write('data: [DONE]\n\n')
                res.end()
                return
              }

              // Send recognized user transcript
              sendSSE({ type: 'transcript', role: 'user', text: userText, isFinal: true })
              history.push({ role: 'user', content: userText })

              sendSSE({ type: 'status', state: 'PROCESSING', message: 'Thinking (NVIDIA NIM)...' })

              // Stream LLM response
              const systemPrompt =
                'You are HSBot Live Voice Assistant powered by NVIDIA NIM. Respond conversationally, concisely, and naturally in 1 to 3 spoken sentences. Do not use Markdown formatting or bullet points since your response will be read aloud.'
              const messagesToSend = [
                { role: 'system', content: systemPrompt },
                ...history.slice(-8),
              ]

              const llmRes = await nvidiaLiveService.chatCompletion(messagesToSend, true)
              let assistantFullText = ''
              let sentenceBuffer = ''
              let chunkIndex = 0
              const voiceName = body.voice || 'Chatterbox-Multilingual'

              const synthesizeAndStreamSentence = async (text: string) => {
                const clean = text.replace(/[*_#`~[\]]/g, '').trim()
                if (clean.length < 2) return
                try {
                  sendSSE({ type: 'status', state: 'SPEAKING', message: 'NVIDIA Voice Speaking...' })
                  const ttsRes = await nvidiaLiveService.synthesizePCM(clean, voiceName, 24000)
                  if (ttsRes && ttsRes.audioBase64) {
                    sendSSE({
                      type: 'audio_chunk',
                      audio: ttsRes.audioBase64,
                      sampleRate: ttsRes.sampleRate,
                      index: chunkIndex++,
                    })
                  }
                } catch (ttsErr: any) {
                  console.warn('[LiveApiPlugin] /turn sentence TTS error:', ttsErr?.message)
                }
              }

              if (llmRes.body) {
                const decoder = new TextDecoder()
                let buffer = ''
                // @ts-ignore
                for await (const chunk of llmRes.body) {
                  buffer += typeof chunk === 'string' ? chunk : decoder.decode(chunk, { stream: true })
                  const lines = buffer.split('\n')
                  buffer = lines.pop() || ''
                  for (const line of lines) {
                    if (line.startsWith('data: ') && !line.includes('[DONE]')) {
                      try {
                        const parsed = JSON.parse(line.substring(6))
                        const content = parsed.choices?.[0]?.delta?.content || ''
                        if (content) {
                          assistantFullText += content
                          sentenceBuffer += content
                          sendSSE({ type: 'llm_chunk', text: content })

                          // Stream audio for completed sentence
                          const match = sentenceBuffer.match(/^(.*?[.!?\n])\s*(.*)$/s)
                          if (match) {
                            const ready = match[1].trim()
                            sentenceBuffer = match[2] || ''
                            if (ready.length >= 3) {
                              await synthesizeAndStreamSentence(ready)
                            }
                          }
                        }
                      } catch (e) {
                        // ignore
                      }
                    }
                  }
                }
              }

              // Synthesize any remaining sentence buffer
              if (sentenceBuffer.trim().length > 0) {
                await synthesizeAndStreamSentence(sentenceBuffer.trim())
              }

              if (!assistantFullText.trim()) {
                assistantFullText = 'I am here and listening.'
              }

              history.push({ role: 'assistant', content: assistantFullText })
              sendSSE({ type: 'transcript', role: 'assistant', text: assistantFullText, isFinal: true })

              sendSSE({ type: 'status', state: 'LISTENING', message: 'Listening...' })
              res.write('data: [DONE]\n\n')
              res.end()
            } catch (err: any) {
              console.error('[LiveApiPlugin] Turn error:', err?.message)
              sendSSE({ type: 'error', code: 'TURN_ERROR', message: err?.message || 'Error processing speech turn' })
              sendSSE({ type: 'status', state: 'LISTENING', message: 'Listening...' })
              res.write('data: [DONE]\n\n')
              res.end()
            }
            return
          }

          // Normal Chat API Endpoints
          if (pathname === '/api/chats' && req.method === 'POST') {
            const body = await parseJsonBody()
            const chatId = crypto.randomUUID()
            const chat = {
              id: chatId,
              title: body.title || 'New Chat',
              created_at: new Date().toISOString(),
              updated_at: new Date().toISOString(),
            }
            inMemoryChats[chatId] = chat
            inMemoryMessages[chatId] = []
            res.setHeader('Content-Type', 'application/json')
            res.end(JSON.stringify(chat))
            return
          }

          if (pathname === '/api/chats' && req.method === 'GET') {
            res.setHeader('Content-Type', 'application/json')
            res.end(JSON.stringify(Object.values(inMemoryChats)))
            return
          }

          if (pathname.startsWith('/api/chats/') && pathname.endsWith('/messages') && req.method === 'GET') {
            const parts = pathname.split('/')
            const chatId = parts[3]
            res.setHeader('Content-Type', 'application/json')
            res.end(JSON.stringify(inMemoryMessages[chatId] || []))
            return
          }

          if (pathname === '/api/nvidia/chat' || pathname === '/api/chats/messages') {
            const body = await parseJsonBody()
            const messages = body.messages || [{ role: 'user', content: body.message || '' }]
            const llmRes = await nvidiaLiveService.chatCompletion(messages, true)

            res.setHeader('Content-Type', 'text/event-stream')
            res.setHeader('Cache-Control', 'no-cache')
            res.setHeader('Connection', 'keep-alive')

            if (llmRes.body) {
              const decoder = new TextDecoder()
              let buffer = ''
              // @ts-ignore
              for await (const chunk of llmRes.body) {
                buffer += typeof chunk === 'string' ? chunk : decoder.decode(chunk, { stream: true })
                const lines = buffer.split('\n')
                buffer = lines.pop() || ''
                for (const line of lines) {
                  const trimmed = line.trim()
                  if (trimmed.startsWith('data: ') && !trimmed.includes('[DONE]')) {
                    try {
                      const parsed = JSON.parse(trimmed.substring(6))
                      const delta = parsed.choices?.[0]?.delta?.content || ''
                      if (delta) {
                        res.write(`data: ${JSON.stringify({ type: 'content', content: delta })}\n\n`)
                      }
                    } catch {
                      // ignore
                    }
                  }
                }
              }
              res.write('data: [DONE]\n\n')
              res.end()
            } else {
              res.end('data: [DONE]\n\n')
            }
            return
          }

          next()
        } catch (err: any) {
          console.error('[LiveApiPlugin] Handler error:', err)
          res.statusCode = 500
          res.setHeader('Content-Type', 'application/json')
          res.end(JSON.stringify({ error: err?.message || 'Internal Live API Error' }))
        }
      })
    },
  }
}
