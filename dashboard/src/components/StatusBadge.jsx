import React from 'react';

const colors = {
  active: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
  running: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
  idle: 'bg-slate-500/20 text-slate-400 border-slate-500/30',
  offline: 'bg-red-500/20 text-red-400 border-red-500/30',
  completed: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
  queued: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  failed: 'bg-red-500/20 text-red-400 border-red-500/30',
  pending: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
  online: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
  degraded: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
  enforced: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
  permissive: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  delivered: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
  read: 'bg-slate-500/20 text-slate-400 border-slate-500/30',
};

const dotColors = {
  active: 'bg-emerald-400', running: 'bg-amber-400', idle: 'bg-slate-400',
  offline: 'bg-red-400', completed: 'bg-emerald-400', queued: 'bg-blue-400',
  failed: 'bg-red-400', pending: 'bg-amber-400', online: 'bg-emerald-400',
  degraded: 'bg-amber-400', enforced: 'bg-emerald-400', permissive: 'bg-blue-400',
  delivered: 'bg-emerald-400', read: 'bg-slate-400',
};

export default function StatusBadge({ status }) {
  return (
    <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 text-xs font-medium rounded-full border ${colors[status] || colors.idle}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${dotColors[status] || dotColors.idle} ${status === 'running' || status === 'active' ? 'animate-pulse' : ''}`} />
      {status}
    </span>
  );
}
