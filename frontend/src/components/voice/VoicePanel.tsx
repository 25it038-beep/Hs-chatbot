'use client'

import React, { useState } from 'react'
import { ChevronDown, Settings, Mic, Volume2, Bell, Languages, Zap } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import { cn } from '@/lib/utils'
import { VoiceOrb } from './VoiceOrb'
import { VoiceConfig } from '@/lib/voice'

interface VoicePanelProps {
  isHandsFree: boolean
  status: string
  audioLevel: number
  wakeWordDetected: boolean
  wsConnected: boolean
  config: VoiceConfig
  onToggle: (enabled: boolean) => void
  onInterrupt?: () => void
  onConfigChange: (config: Partial<VoiceConfig>) => void
  className?: string
}

export function VoicePanel({
  isHandsFree,
  status,
  audioLevel,
  wakeWordDetected,
  wsConnected,
  config,
  onToggle,
  onInterrupt,
  onConfigChange,
  className,
}: VoicePanelProps) {
  const [isSettingsOpen, setIsSettingsOpen] = useState(false)

  const handleConfigChange = (key: keyof VoiceConfig, value: any) => {
    onConfigChange({ [key]: value })
  }

  return (
    <div className={cn('space-y-4', className)}>
      {/* Voice Orb */}
      <VoiceOrb
        status={status}
        audioLevel={audioLevel}
        isHandsFree={isHandsFree}
        wakeWordDetected={wakeWordDetected}
        wsConnected={wsConnected}
        onToggle={onToggle}
        onInterrupt={onInterrupt}
      />

      {/* Settings Panel */}
      <AnimatePresence mode="wait">
        {isSettingsOpen ? (
          <motion.div
            key="settings-open"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden"
          >
            <div className="rounded-xl border border-border bg-card p-4 space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="font-semibold text-foreground">Voice Settings</h3>
                <button
                  onClick={() => setIsSettingsOpen(false)}
                  className="p-1 rounded hover:bg-muted transition-colors"
                  aria-label="Close settings"
                >
                  <ChevronDown className="w-5 h-5 rotate-180" />
                </button>
              </div>

              <div className="space-y-4">
                {/* Wake Word */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <Zap className="w-5 h-5 text-muted-foreground" />
                    <div>
                      <p className="font-medium text-foreground">Wake Word</p>
                      <p className="text-sm text-muted-foreground">Activate with "Hey HS"</p>
                    </div>
                  </div>
                  <button
                    onClick={() => handleConfigChange('wakeWordEnabled', !config.wakeWordEnabled)}
                    className={cn(
                      'relative w-12 h-6 rounded-full transition-colors',
                      config.wakeWordEnabled ? 'bg-primary' : 'bg-muted'
                    )}
                    aria-label={config.wakeWordEnabled ? 'Disable wake word' : 'Enable wake word'}
                    role="switch"
                    aria-checked={config.wakeWordEnabled}
                  >
                    <span
                      className={cn(
                        'absolute top-0.5 w-5 h-5 rounded-full bg-white shadow transition-transform',
                        config.wakeWordEnabled ? 'left-5.5' : 'left-0.5'
                      )}
                    />
                  </button>
                </div>

                {config.wakeWordEnabled && (
                  <div className="pl-8 space-y-2 border-l-2 border-border ml-4">
                    <label className="block text-sm font-medium text-foreground">
                      Wake Phrase
                    </label>
                    <input
                      type="text"
                      value={config.wakeWord}
                      onChange={(e) => handleConfigChange('wakeWord', e.target.value)}
                      className="w-full px-3 py-2 rounded-md border border-input bg-background text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                      placeholder="Hey HS"
                    />
                    <p className="text-xs text-muted-foreground">
                      Change the wake word phrase (requires restart)
                    </p>
                  </div>
                )}

                {/* Auto Speak */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <Volume2 className="w-5 h-5 text-muted-foreground" />
                    <div>
                      <p className="font-medium text-foreground">Auto Speak Responses</p>
                      <p className="text-sm text-muted-foreground">Automatically play AI responses</p>
                    </div>
                  </div>
                  <button
                    onClick={() => handleConfigChange('autoSpeak', !config.autoSpeak)}
                    className={cn(
                      'relative w-12 h-6 rounded-full transition-colors',
                      config.autoSpeak ? 'bg-primary' : 'bg-muted'
                    )}
                    aria-label={config.autoSpeak ? 'Disable auto speak' : 'Enable auto speak'}
                    role="switch"
                    aria-checked={config.autoSpeak}
                  >
                    <span
                      className={cn(
                        'absolute top-0.5 w-5 h-5 rounded-full bg-white shadow transition-transform',
                        config.autoSpeak ? 'left-5.5' : 'left-0.5'
                      )}
                    />
                  </button>
                </div>

                {/* Interrupt AI */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <Zap className="w-5 h-5 text-muted-foreground" />
                    <div>
                      <p className="font-medium text-foreground">Interrupt AI</p>
                      <p className="text-sm text-muted-foreground">Stop AI speech by speaking</p>
                    </div>
                  </div>
                  <button
                    onClick={() => handleConfigChange('interruptEnabled', !config.interruptEnabled)}
                    className={cn(
                      'relative w-12 h-6 rounded-full transition-colors',
                      config.interruptEnabled ? 'bg-primary' : 'bg-muted'
                    )}
                    aria-label={config.interruptEnabled ? 'Disable interruption' : 'Enable interruption'}
                    role="switch"
                    aria-checked={config.interruptEnabled}
                  >
                    <span
                      className={cn(
                        'absolute top-0.5 w-5 h-5 rounded-full bg-white shadow transition-transform',
                        config.interruptEnabled ? 'left-5.5' : 'left-0.5'
                      )}
                    />
                  </button>
                </div>

                {/* Voice Selection */}
                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">
                    Voice
                  </label>
                  <select
                    value={config.voice}
                    onChange={(e) => handleConfigChange('voice', e.target.value)}
                    className="w-full px-3 py-2 rounded-md border border-input bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                  >
                    <option value="en-US-Female-1">English (US) - Female 1</option>
                    <option value="en-US-Male-1">English (US) - Male 1</option>
                    <option value="en-GB-Female-1">English (UK) - Female 1</option>
                    <option value="ta-IN-Female-1">Tamil (India) - Female 1</option>
                    <option value="ta-IN-Male-1">Tamil (India) - Male 1</option>
                  </select>
                </div>

                {/* Language */}
                <div>
                  <label className="block text-sm font-medium text-foreground mb-2 flex items-center gap-2">
                    <Languages className="w-4 h-4" />
                    Language
                  </label>
                  <select
                    value={config.language}
                    onChange={(e) => handleConfigChange('language', e.target.value)}
                    className="w-full px-3 py-2 rounded-md border border-input bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                  >
                    <option value="en-US">English (US)</option>
                    <option value="en-GB">English (UK)</option>
                    <option value="ta-IN">Tamil (India)</option>
                    <option value="auto">Auto Detect</option>
                  </select>
                </div>

                {/* Silence Timeout */}
                <div>
                  <label className="block text-sm font-medium text-foreground mb-2 flex items-center gap-2">
                    <Bell className="w-4 h-4" />
                    Silence Timeout: {config.silenceTimeout}ms
                  </label>
                  <input
                    type="range"
                    min="500"
                    max="5000"
                    step="500"
                    value={config.silenceTimeout}
                    onChange={(e) => handleConfigChange('silenceTimeout', parseInt(e.target.value))}
                    className="w-full h-2 bg-muted rounded-lg appearance-none accent-primary"
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    Wait this long after speech ends before processing
                  </p>
                </div>

                {/* Min Speech Duration */}
                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">
                    Minimum Speech Duration: {config.minSpeechDuration}ms
                  </label>
                  <input
                    type="range"
                    min="200"
                    max="2000"
                    step="100"
                    value={config.minSpeechDuration}
                    onChange={(e) => handleConfigChange('minSpeechDuration', parseInt(e.target.value))}
                    className="w-full h-2 bg-muted rounded-lg appearance-none accent-primary"
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    Minimum speech length to consider valid
                  </p>
                </div>
              </div>
            </div>
          </motion.div>
        ) : (
          <motion.div
            key="settings-closed"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 0, height: 0 }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden"
          />
        )}
      </AnimatePresence>

      {/* Settings Toggle Button */}
      <button
        onClick={() => setIsSettingsOpen(!isSettingsOpen)}
        className={cn(
          'w-full p-3 rounded-xl border border-border bg-card transition-all duration-200',
          isSettingsOpen && 'border-primary'
        )}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Settings className="w-5 h-5 text-muted-foreground" />
            <div>
              <p className="font-medium text-foreground">Voice Settings</p>
              <p className="text-sm text-muted-foreground">
                Configure voice, wake word, and behavior
              </p>
            </div>
          </div>
          <ChevronDown
            className={cn(
              'w-5 h-5 text-muted-foreground transition-transform duration-200',
              isSettingsOpen && 'rotate-180'
            )}
          />
        </div>
      </button>
    </div>
  )
}