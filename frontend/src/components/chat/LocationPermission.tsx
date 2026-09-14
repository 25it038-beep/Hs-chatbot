import React, { useState } from 'react';

export const LocationPermission: React.FC = () => {
  const [city, setCity] = useState('');
  const [saved, setSaved] = useState<string | null>(null);

  const saveLocation = () => {
    if (!city.trim()) return;
    localStorage.setItem('hsbot_location', city.trim());
    setSaved(city.trim());
  };

  const clearLocation = () => {
    localStorage.removeItem('hsbot_location');
    setSaved(null);
    setCity('');
  };

  return (
    <div className="mt-2 text-xs opacity-80">
      <div className="flex gap-2 items-center">
        <input
          placeholder="Set your city for weather/time"
          value={city}
          onChange={(e) => setCity(e.target.value)}
          className="px-2 py-1 rounded border bg-transparent"
        />
        <button onClick={saveLocation} className="px-2 py-1 rounded bg-zinc-200 dark:bg-zinc-800">Save</button>
        {saved && <button onClick={clearLocation} className="px-2 py-1 rounded bg-zinc-200 dark:bg-zinc-800">Clear</button>}
      </div>
      <div className="mt-1">Location is stored locally and only used for time/weather queries. No tracking.</div>
    </div>
  );
};
