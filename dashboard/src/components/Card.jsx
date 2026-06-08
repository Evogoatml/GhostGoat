import React from 'react';

export default function Card({ children, className = '' }) {
  return (
    <div className={`bg-[#1a1d2e] border border-[#252836] rounded-xl ${className}`}>
      {children}
    </div>
  );
}

export function CardHeader({ icon: Icon, title, iconColor = 'text-indigo-400', children }) {
  return (
    <div className="flex items-center justify-between px-5 py-4 border-b border-[#252836]">
      <div className="flex items-center gap-2">
        {Icon && <Icon className={`w-5 h-5 ${iconColor}`} />}
        <h3 className="text-sm font-semibold text-white">{title}</h3>
      </div>
      {children}
    </div>
  );
}
