import React from 'react';

export default function KPICard({ icon: Icon, label, value, sub, color = 'indigo' }) {
  const colors = {
    indigo: 'from-indigo-600/20 to-indigo-800/10 border-indigo-500/20 text-indigo-400',
    emerald: 'from-emerald-600/20 to-emerald-800/10 border-emerald-500/20 text-emerald-400',
    amber: 'from-amber-600/20 to-amber-800/10 border-amber-500/20 text-amber-400',
    red: 'from-red-600/20 to-red-800/10 border-red-500/20 text-red-400',
    purple: 'from-purple-600/20 to-purple-800/10 border-purple-500/20 text-purple-400',
    blue: 'from-blue-600/20 to-blue-800/10 border-blue-500/20 text-blue-400',
  };

  return (
    <div className={`bg-gradient-to-br ${colors[color]} border rounded-xl p-4`}>
      <div className="flex items-center gap-2 mb-2">
        {Icon && <Icon className="w-4 h-4 opacity-70" />}
        <span className="text-xs font-medium uppercase tracking-wider opacity-70">{label}</span>
      </div>
      <div className="text-2xl font-bold text-white">{value}</div>
      {sub && <div className="text-xs opacity-60 mt-1">{sub}</div>}
    </div>
  );
}
