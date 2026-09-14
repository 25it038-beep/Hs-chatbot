import React from 'react';

export type ToolStatusType = 'time' | 'weather' | 'location' | 'search';

export const ToolStatus: React.FC<{ tool: ToolStatusType; label: string }> = ({ tool, label }) => {
  const colors: Record<ToolStatusType, string> = {
    time: 'bg-blue-500',
    weather: 'bg-sky-500',
    location: 'bg-emerald-500',
    search: 'bg-amber-500',
  };
  return (
    <div className="flex items-center gap-2 text-xs opacity-80">
      <span className={`inline-block w-2 h-2 rounded-full ${colors[tool]}`} />
      {label}
    </div>
  );
};
