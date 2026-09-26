/*
 * useVoiceService React Hook
 * Custom hook for WebSocket communication with the voice service
 */
import { useState, useEffect, useCallback, useRef } from 'react';
import { getBaseUrl, getWsBaseUrl } from '@/lib/api';

export interface VoiceEvent {
  type: 'wake_word' | 'command' | 'error' | 'state_change' | 'status';
  timestamp: string;
  data: any;
}

interface UseVoiceServiceOptions {
  enabled?: boolean;
  onWakeWord?: (data: any) => void;
  onCommand?: (data: any) => void;
  onError?: (error: string) => void;
  onStateChange?: (state: string) => void;
}

export const useVoiceService = (options: UseVoiceServiceOptions = {}) => {
  const {
    enabled = true,
    onWakeWord,
    onCommand,
    onError,
    onStateChange,
  } = options;

  const [isConnected, setIsConnected] = useState(false);
  const [state, setState] = useState<string>('stopped');
  const [error, setError] = useState<string | null>(null);
  const [isListening, setIsListening] = useState(false);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectAttempts = useRef(0);
  const MAX_RECONNECT_ATTEMPTS = 5;
  const RECONNECT_DELAY = 3000;

  const connect = useCallback(() => {
    if (!enabled || wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    try {
      const wsUrl = `${getWsBaseUrl()}/voice/ws`;

      wsRef.current = new WebSocket(wsUrl);

      wsRef.current.onopen = () => {
        console.log('Voice service connected');
        setIsConnected(true);
        setError(null);
        reconnectAttempts.current = 0;
      };

      wsRef.current.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          const voiceEvent: VoiceEvent = {
            type: message.type,
            timestamp: message.timestamp || new Date().toISOString(),
            data: message.data,
          };

          switch (voiceEvent.type) {
            case 'wake_word':
              onWakeWord?.(voiceEvent.data);
              break;
            case 'command':
              onCommand?.(voiceEvent.data);
              break;
            case 'error':
              setError(voiceEvent.data.error);
              onError?.(voiceEvent.data.error);
              break;
            case 'state_change':
              setState(voiceEvent.data.new_state);
              onStateChange?.(voiceEvent.data.new_state);
              break;
            case 'status':
              setState(voiceEvent.data.state);
              setIsListening(voiceEvent.data.state !== 'stopped');
              break;
          }
        } catch (err) {
          console.error('Error parsing voice service message:', err);
        }
      };

      wsRef.current.onerror = (event) => {
        console.error('Voice service WebSocket error:', event);
        setError('Voice service connection error');
        onError?.('Connection error');
      };

      wsRef.current.onclose = () => {
        console.log('Voice service disconnected');
        setIsConnected(false);
        wsRef.current = null;

        // Attempt to reconnect
        if (enabled && reconnectAttempts.current < MAX_RECONNECT_ATTEMPTS) {
          reconnectAttempts.current += 1;
          console.log(
            `Attempting to reconnect (${reconnectAttempts.current}/${MAX_RECONNECT_ATTEMPTS})...`
          );

          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, RECONNECT_DELAY * reconnectAttempts.current);
        }
      };
    } catch (err) {
      console.error('Error connecting to voice service:', err);
      setError('Failed to connect to voice service');
    }
  }, [enabled, onWakeWord, onCommand, onError, onStateChange]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.close();
    }
  }, []);

  const startListener = useCallback(async () => {
    try {
      const response = await fetch(`${getBaseUrl()}/voice/listener/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ device_id: 'default' }),
      });

      if (response.ok) {
        const data = await response.json();
        setState(data.state);
        setIsListening(true);
      } else {
        const error = await response.text();
        setError(error);
        throw new Error(error);
      }
    } catch (err) {
      console.error('Error starting listener:', err);
      setError(err instanceof Error ? err.message : 'Failed to start listener');
    }
  }, []);

  const stopListener = useCallback(async () => {
    try {
      const response = await fetch(`${getBaseUrl()}/voice/listener/stop`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ device_id: 'default' }),
      });

      if (response.ok) {
        setState('stopped');
        setIsListening(false);
      } else {
        throw new Error('Failed to stop listener');
      }
    } catch (err) {
      console.error('Error stopping listener:', err);
    }
  }, []);

  const setMicrophoneEnabled = useCallback(async (enabled: boolean) => {
    try {
      const response = await fetch(`${getBaseUrl()}/voice/listener/mic-enable`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ device_id: 'default', enabled }),
      });

      if (!response.ok) {
        throw new Error('Failed to control microphone');
      }
    } catch (err) {
      console.error('Error controlling microphone:', err);
    }
  }, []);

  const sendCommand = useCallback(async (command: string) => {
    try {
      const response = await fetch(`${getBaseUrl()}/voice/automation/execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          org_id: 'default',
          user_id: 'default',
          command_text: command,
        }),
      });

      if (response.ok) {
        return await response.json();
      } else {
        throw new Error('Failed to execute command');
      }
    } catch (err) {
      console.error('Error executing command:', err);
      setError(err instanceof Error ? err.message : 'Command execution failed');
    }
  }, []);

  // Auto-connect on mount
  useEffect(() => {
    if (enabled) {
      connect();
    }

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, [enabled, connect]);

  return {
    isConnected,
    state,
    error,
    isListening,
    connect,
    disconnect,
    startListener,
    stopListener,
    setMicrophoneEnabled,
    sendCommand,
  };
};

export default useVoiceService;
