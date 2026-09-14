import React from 'react';

type WeatherData = {
  location?: string;
  current?: {
    temperature?: number;
    feels_like?: number;
    condition?: string;
    humidity?: number;
    wind_speed?: number;
    rain_probability?: number;
  };
  forecast?: Array<{
    date: string;
    temp_max?: number;
    temp_min?: number;
    condition?: string;
    rain_probability?: number;
  }>;
};

export const WeatherCard: React.FC<{ data: WeatherData }> = ({ data }) => {
  if (!data?.current) return null;
  const cur = data.current;
  return (
    <div className="mt-3 rounded-xl border border-zinc-200 dark:border-zinc-800 p-4 bg-white/60 dark:bg-zinc-900/60">
      <div className="flex items-center justify-between">
        <h4 className="font-semibold">{data.location || 'Weather'}</h4>
        <span className="text-sm opacity-70">{cur.condition}</span>
      </div>
      <div className="mt-2 grid grid-cols-3 gap-3 text-sm">
        <div>
          <div className="text-2xl font-bold">{Math.round(cur.temperature ?? 0)}°C</div>
          <div className="opacity-70">Feels like {Math.round(cur.feels_like ?? 0)}°C</div>
        </div>
        <div className="opacity-80">
          <div>Humidity {cur.humidity}%</div>
          <div>Wind {cur.wind_speed} km/h</div>
          <div>Rain {cur.rain_probability}%</div>
        </div>
        <div className="text-right">
          <div className="text-xs opacity-70">Next 3 days</div>
          <div className="space-y-1">
            {(data.forecast || []).slice(0,3).map((d, i) => (
              <div key={i} className="text-xs">
                {new Date(d.date).toLocaleDateString(undefined,{weekday:'short'})} {d.temp_min?.toFixed(0)}°/{d.temp_max?.toFixed(0)}°
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
