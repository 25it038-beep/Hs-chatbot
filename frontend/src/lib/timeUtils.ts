export type DeviceTime = {
  time: string;
  date: string;
  day: string;
  timezone: string;
};

export function getDeviceTime(): DeviceTime {
  const now = new Date();
  return {
    time: now.toLocaleTimeString(),
    date: now.toLocaleDateString(undefined, { year: 'numeric', month: 'long', day: 'numeric' }),
    day: now.toLocaleDateString(undefined, { weekday: 'long' }),
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
  };
}

export function formatTimeForDisplay(t: DeviceTime): string {
  return `🕐 It's ${t.time} on ${t.day}, ${t.date}.`;
}
