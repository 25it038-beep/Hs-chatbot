/*
 * Microphone Status Indicator Component
 * React component for displaying voice listener state
 */
import React, { useEffect, useState } from 'react';
import { Mic, MicOff, Loader2, AlertCircle } from 'lucide-react';

export type MicrophoneState = 'idle' | 'listening' | 'processing' | 'command_active' | 'stopped' | 'error';

interface MicrophoneStatusProps {
  deviceId?: string;
  onStateChange?: (state: MicrophoneState) => void;
  autoRefresh?: boolean;
  refreshInterval?: number;
}

const STATE_CONFIG: Record<MicrophoneState, { color: string; label: string; icon: React.ReactNode }> = {
  idle: {
    color: 'bg-gray-500',
    label: 'Idle',
    icon: <MicOff className="w-4 h-4" />,
  },
  listening: {
    color: 'bg-blue-500',
    label: 'Listening',
    icon: <Mic className="w-4 h-4 animate-pulse" />,
  },
  processing: {
    color: 'bg-yellow-500',
    label: 'Processing',
    icon: <Loader2 className="w-4 h-4 animate-spin" />,
  },
  command_active: {
    color: 'bg-green-500',
    label: 'Active',
    icon: <Mic className="w-4 h-4" />,
  },
  stopped: {
    color: 'bg-gray-600',
    label: 'Stopped',
    icon: <MicOff className="w-4 h-4" />,
  },
  error: {
    color: 'bg-red-500',
    label: 'Error',
    icon: <AlertCircle className="w-4 h-4" />,
  },
};

export const MicrophoneStatus: React.FC<MicrophoneStatusProps> = ({
  deviceId = 'default',
  onStateChange,
  autoRefresh = true,
  refreshInterval = 1000,
}) => {
  const [state, setState] = useState<MicrophoneState>('idle');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!autoRefresh) return;

    const interval = setInterval(async () => {
      setLoading(true);
      try {
        const response = await fetch(`/api/voice/status?device_id=${deviceId}`);
        if (response.ok) {
          const data = await response.json();
          const newState = data.state as MicrophoneState;
          setState(newState);
          if (onStateChange) {
            onStateChange(newState);
          }
        }
      } catch (error) {
        console.error('Error fetching microphone status:', error);
        setState('error');
      } finally {
        setLoading(false);
      }
    }, refreshInterval);

    return () => clearInterval(interval);
  }, [deviceId, autoRefresh, refreshInterval, onStateChange]);

  const config = STATE_CONFIG[state];

  return (
    <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-gray-100">
      <div className={`${config.color} p-2 rounded-full text-white`}>
        {config.icon}
      </div>
      <span className="text-sm font-medium text-gray-900">{config.label}</span>
      {loading && <Loader2 className="w-3 h-3 animate-spin text-gray-600 ml-auto" />}
    </div>
  );
};

// Inline version for compact display
export const MicrophoneStatusInline: React.FC<Omit<MicrophoneStatusProps, 'autoRefresh'>> = ({
  deviceId = 'default',
  onStateChange,
  refreshInterval = 2000,
}) => {
  const [state, setState] = useState<MicrophoneState>('idle');

  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        const response = await fetch(`/api/voice/status?device_id=${deviceId}`);
        if (response.ok) {
          const data = await response.json();
          const newState = data.state as MicrophoneState;
          setState(newState);
          if (onStateChange) {
            onStateChange(newState);
          }
        }
      } catch (error) {
        console.error('Error fetching microphone status:', error);
      }
    }, refreshInterval);

    return () => clearInterval(interval);
  }, [deviceId, refreshInterval, onStateChange]);

  const config = STATE_CONFIG[state];
  const isActive = state === 'listening' || state === 'processing' || state === 'command_active';

  return (
    <div
      className={`inline-flex items-center gap-1 px-2 py-1 rounded text-xs font-medium ${
        isActive ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
      }`}
    >
      <div className={`${config.color} w-2 h-2 rounded-full`} />
      {config.label}
    </div>
  );
};

// Full screen overlay component for active voice command
export const VoiceCommandOverlay: React.FC<{ isActive: boolean }> = ({ isActive }) => {
  if (!isActive) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 pointer-events-none">
      <div className="bg-white rounded-2xl p-8 text-center space-y-4">
        <div className="flex justify-center">
          <div className="relative w-24 h-24">
            <div className="absolute inset-0 rounded-full bg-blue-500 opacity-25 animate-ping" />
            <div className="absolute inset-2 rounded-full bg-blue-500 opacity-50 animate-pulse" />
            <Mic className="absolute inset-0 m-auto w-12 h-12 text-blue-600" />
          </div>
        </div>
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Listening...</h2>
          <p className="text-gray-600 mt-2">Speak your command</p>
        </div>
      </div>
    </div>
  );
};

export default MicrophoneStatus;
