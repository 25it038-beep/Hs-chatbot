import React, { useEffect, useState } from 'react';

export const LocationSettings: React.FC = () => {
  const [city, setCity] = useState<string>(() => localStorage.getItem('hsbot_location') || '');
  const [useDevice, setUseDevice] = useState<boolean>(() => localStorage.getItem('hsbot_use_device') === 'true');

  useEffect(() => {
    localStorage.setItem('hsbot_location', city);
  }, [city]);

  useEffect(() => {
    localStorage.setItem('hsbot_use_device', String(useDevice));
  }, [useDevice]);

  const requestDeviceLocation = () => {
    if (!navigator.geolocation) {
      alert('Geolocation not supported');
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const lat = pos.coords.latitude;
        const lon = pos.coords.longitude;
        localStorage.setItem('hsbot_device_coords', `${lat},${lon}`);
        setUseDevice(true);
        alert('Location permission granted');
      },
      (err) => {
        alert('Location permission denied');
      }
    );
  };

  const clearLocation = () => {
    localStorage.removeItem('hsbot_location');
    localStorage.removeItem('hsbot_device_coords');
    setCity('');
    setUseDevice(false);
  };

  return (
    <div className="space-y-3">
      <div className="p-3.5 rounded-xl border border-border/60 bg-muted/30">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium">Use device location</span>
          <button
            onClick={() => setUseDevice(!useDevice)}
            className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${useDevice ? 'bg-brand' : 'bg-muted-foreground/25'}`}
          >
            <span className={`inline-block h-4 w-4 rounded-full bg-white transition-transform ${useDevice ? 'translate-x-[18px]' : 'translate-x-0.5'}`} />
          </button>
        </div>
        {useDevice && (
          <button onClick={requestDeviceLocation} className="text-xs underline text-muted-foreground/70">Allow location access</button>
        )}
      </div>

      <div className="p-3.5 rounded-xl border border-border/60 bg-muted/30">
        <label className="text-sm font-medium">Selected city</label>
        <div className="flex gap-2 mt-2">
          <input
            value={city}
            onChange={(e) => setCity(e.target.value)}
            placeholder="Chennai, Mumbai, London..."
            className="flex-1 px-2 py-1 rounded border bg-background text-sm"
          />
          <button onClick={clearLocation} className="px-2 py-1 rounded bg-muted text-xs">Clear</button>
        </div>
        <p className="text-xs text-muted-foreground/60 mt-2">Current: {city || 'Not set'}</p>
      </div>
    </div>
  );
};
