/*
 * Voice Settings UI Component
 * Frontend: React component for managing voice automation settings
 */
import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Toggle } from '@/components/ui/toggle';
import { Slider } from '@/components/ui/slider';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Loader2, Mic, Settings, Volume2, Shield, Zap } from 'lucide-react';

interface VoiceSettings {
  always_listening: boolean;
  wake_word: string;
  voice_match_enabled: boolean;
  continuous_conversation_enabled: boolean;
  voice_response_enabled: boolean;
  activation_timeout: number;
  microphone: string;
  anti_spoofing: boolean;
}

export const VoiceSettings: React.FC = () => {
  const [settings, setSettings] = useState<VoiceSettings>({
    always_listening: true,
    wake_word: 'Wake up',
    voice_match_enabled: true,
    continuous_conversation_enabled: false,
    voice_response_enabled: true,
    activation_timeout: 10,
    microphone: 'default',
    anti_spoofing: true,
  });

  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [devices, setDevices] = useState<any[]>([]);

  useEffect(() => {
    loadSettings();
    loadDevices();
  }, []);

  const loadSettings = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/voice/settings');
      if (response.ok) {
        const data = await response.json();
        setSettings(data);
      }
    } catch (error) {
      console.error('Error loading voice settings:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadDevices = async () => {
    try {
      const response = await fetch('/api/voice/devices');
      if (response.ok) {
        const data = await response.json();
        setDevices(data);
      }
    } catch (error) {
      console.error('Error loading devices:', error);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const response = await fetch('/api/voice/settings', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings),
      });
      if (response.ok) {
        // Show success toast
        console.log('Settings saved successfully');
      }
    } catch (error) {
      console.error('Error saving settings:', error);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="w-8 h-8 animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Always Listening */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Mic className="w-5 h-5" />
            Always Listening
          </CardTitle>
          <CardDescription>
            Enable background voice activation monitoring
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium">Passive Listening Mode</p>
              <p className="text-sm text-gray-600">
                Microphone always active, waiting for wake word
              </p>
            </div>
            <Toggle
              pressed={settings.always_listening}
              onPressedChange={(pressed: boolean) =>
                setSettings({ ...settings, always_listening: pressed })
              }
              aria-label="Toggle always listening"
            />
          </div>
        </CardContent>
      </Card>

      {/* Wake Word Configuration */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Zap className="w-5 h-5" />
            Wake Word
          </CardTitle>
          <CardDescription>
            Configure the phrase that activates voice commands
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Select value={settings.wake_word} onValueChange={(value: string) =>
            setSettings({ ...settings, wake_word: value })
          }>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="Wake up">Wake up</SelectItem>
              <SelectItem value="Hey Assistant">Hey Assistant</SelectItem>
              <SelectItem value="HS">HS</SelectItem>
              <SelectItem value="Hey HSBot">Hey HSBot</SelectItem>
            </SelectContent>
          </Select>
          <p className="text-sm text-gray-600">
            You can activate the assistant by saying "{settings.wake_word}"
          </p>
        </CardContent>
      </Card>

      {/* Voice Match */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="w-5 h-5" />
            Voice Match (Speaker Verification)
          </CardTitle>
          <CardDescription>
            Verify user identity via voice recognition
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium">Enable Voice Verification</p>
              <p className="text-sm text-gray-600">
                Only commands from enrolled voices are executed
              </p>
            </div>
            <Toggle
              pressed={settings.voice_match_enabled}
              onPressedChange={(pressed: boolean) =>
                setSettings({ ...settings, voice_match_enabled: pressed })
              }
              aria-label="Toggle voice match"
            />
          </div>

          {settings.voice_match_enabled && (
            <Button variant="outline" className="w-full">
              Enroll New Voice Profile
            </Button>
          )}
        </CardContent>
      </Card>

      {/* Continuous Conversation */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Volume2 className="w-5 h-5" />
            Continuous Conversation Mode
          </CardTitle>
          <CardDescription>
            Stay in active listening mode after wake word
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium">Enable Continuous Mode</p>
              <p className="text-sm text-gray-600">
                After wake word, listen for multiple commands
              </p>
            </div>
            <Toggle
              pressed={settings.continuous_conversation_enabled}
              onPressedChange={(pressed: boolean) =>
                setSettings({
                  ...settings,
                  continuous_conversation_enabled: pressed,
                })
              }
              aria-label="Toggle continuous conversation"
            />
          </div>

          {settings.continuous_conversation_enabled && (
            <div className="space-y-2">
              <label className="text-sm font-medium">
                Conversation Timeout: {settings.activation_timeout}s
              </label>
              <Slider
                value={[settings.activation_timeout]}
                onValueChange={(value: number[]) =>
                  setSettings({
                    ...settings,
                    activation_timeout: value[0],
                  })
                }
                min={5}
                max={60}
                step={5}
                className="w-full"
              />
            </div>
          )}
        </CardContent>
      </Card>

      {/* Anti-Spoofing */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="w-5 h-5" />
            Anti-Spoofing Protection
          </CardTitle>
          <CardDescription>
            Detect and reject fake/replayed audio
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium">Enable Anti-Spoofing</p>
              <p className="text-sm text-gray-600">
                Detect replay attacks and synthetic voices
              </p>
            </div>
            <Toggle
              pressed={settings.anti_spoofing}
              onPressedChange={(pressed: boolean) =>
                setSettings({ ...settings, anti_spoofing: pressed })
              }
              aria-label="Toggle anti-spoofing"
            />
          </div>
        </CardContent>
      </Card>

      {/* Voice Response */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Volume2 className="w-5 h-5" />
            Voice Responses
          </CardTitle>
          <CardDescription>
            Audio feedback for voice commands
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium">Enable Voice Responses</p>
              <p className="text-sm text-gray-600">
                Hear confirmation and responses via audio
              </p>
            </div>
            <Toggle
              pressed={settings.voice_response_enabled}
              onPressedChange={(pressed: boolean) =>
                setSettings({ ...settings, voice_response_enabled: pressed })
              }
              aria-label="Toggle voice responses"
            />
          </div>
        </CardContent>
      </Card>

      {/* Microphone Selection */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Mic className="w-5 h-5" />
            Microphone Selection
          </CardTitle>
          <CardDescription>
            Choose which microphone to use
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Select value={settings.microphone} onValueChange={(value: string) =>
            setSettings({ ...settings, microphone: value })
          }>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="default">Default Microphone</SelectItem>
              {devices.map((device) => (
                <SelectItem key={device.id} value={device.id}>
                  {device.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </CardContent>
      </Card>

      {/* Save Button */}
      <div className="flex gap-2">
        <Button onClick={handleSave} disabled={saving} className="flex-1">
          {saving ? (
            <>
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              Saving...
            </>
          ) : (
            'Save Settings'
          )}
        </Button>
        <Button onClick={loadSettings} variant="outline">
          Reset
        </Button>
      </div>
    </div>
  );
};

export default VoiceSettings;
