import React from 'react';
import { Activity, Cpu, HardDrive, Timer, Gauge } from 'lucide-react';
import {
  AreaChart, Area, LineChart, Line, BarChart, Bar,
  XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
} from 'recharts';
import Card, { CardHeader } from '../components/Card';
import KPICard from '../components/KPICard';
import StatusBadge from '../components/StatusBadge';
import { useGhostGoat } from '../HybridContext';

export default function SystemMonitor() {
  const { agents, chartMetrics: metrics, stats, systemMetrics } = useGhostGoat();
  const activeAgents = agents.filter(a => a.status !== 'offline');
  // Use real system metrics when available, otherwise last chart point
  const last = systemMetrics
    ? { cpu: systemMetrics.cpu_percent, memory: systemMetrics.memory_percent, latency: 0, tasks: stats.runningTasks }
    : (metrics[metrics.length - 1] || {});

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold">System Monitor</h1>
        <p className="text-sm text-slate-400 mt-1">Real-time performance metrics and resource utilization</p>
      </div>

      {/* Live KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <KPICard icon={Cpu} label="CPU Now" value={`${last.cpu || 0}%`} color="indigo" />
        <KPICard icon={HardDrive} label="Memory Now" value={`${last.memory || 0}%`} color="emerald" />
        <KPICard icon={Timer} label="Latency" value={`${last.latency || 0}ms`} color="amber" />
        <KPICard icon={Gauge} label="Tasks/min" value={last.tasks || 0} color="purple" />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader icon={Cpu} title="CPU Utilization (60m)" iconColor="text-indigo-400" />
          <div className="p-4 h-72">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={metrics}>
                <defs>
                  <linearGradient id="cpuFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#6366f1" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#252836" />
                <XAxis dataKey="time" tick={{ fontSize: 10, fill: '#64748b' }} interval={9} />
                <YAxis tick={{ fontSize: 10, fill: '#64748b' }} domain={[0, 100]} />
                <Tooltip contentStyle={{ background: '#1a1d2e', border: '1px solid #252836', borderRadius: 8, fontSize: 12 }} />
                <Area type="monotone" dataKey="cpu" stroke="#6366f1" fill="url(#cpuFill)" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </Card>

        <Card>
          <CardHeader icon={HardDrive} title="Memory Utilization (60m)" iconColor="text-emerald-400" />
          <div className="p-4 h-72">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={metrics}>
                <defs>
                  <linearGradient id="memFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10b981" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#252836" />
                <XAxis dataKey="time" tick={{ fontSize: 10, fill: '#64748b' }} interval={9} />
                <YAxis tick={{ fontSize: 10, fill: '#64748b' }} domain={[0, 100]} />
                <Tooltip contentStyle={{ background: '#1a1d2e', border: '1px solid #252836', borderRadius: 8, fontSize: 12 }} />
                <Area type="monotone" dataKey="memory" stroke="#10b981" fill="url(#memFill)" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </Card>

        <Card>
          <CardHeader icon={Timer} title="Latency Distribution (60m)" iconColor="text-amber-400" />
          <div className="p-4 h-72">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={metrics}>
                <CartesianGrid strokeDasharray="3 3" stroke="#252836" />
                <XAxis dataKey="time" tick={{ fontSize: 10, fill: '#64748b' }} interval={9} />
                <YAxis tick={{ fontSize: 10, fill: '#64748b' }} />
                <Tooltip contentStyle={{ background: '#1a1d2e', border: '1px solid #252836', borderRadius: 8, fontSize: 12 }} />
                <Line type="monotone" dataKey="latency" stroke="#f59e0b" strokeWidth={2} dot={false} name="Latency ms" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card>

        <Card>
          <CardHeader icon={Gauge} title="Task Throughput (60m)" iconColor="text-purple-400" />
          <div className="p-4 h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={metrics.slice(-20)}>
                <CartesianGrid strokeDasharray="3 3" stroke="#252836" />
                <XAxis dataKey="time" tick={{ fontSize: 10, fill: '#64748b' }} />
                <YAxis tick={{ fontSize: 10, fill: '#64748b' }} />
                <Tooltip contentStyle={{ background: '#1a1d2e', border: '1px solid #252836', borderRadius: 8, fontSize: 12 }} />
                <Bar dataKey="tasks" fill="#8b5cf6" radius={[4, 4, 0, 0]} name="Tasks/min" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>

      {/* Per-agent resource table */}
      <Card>
        <CardHeader icon={Activity} title="Per-Agent Resources" iconColor="text-cyan-400" />
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-[10px] text-slate-500 uppercase tracking-wider border-b border-[#252836]">
                <th className="text-left px-5 py-3">Agent</th>
                <th className="text-left px-5 py-3">Status</th>
                <th className="text-left px-5 py-3">CPU</th>
                <th className="text-left px-5 py-3">Memory</th>
                <th className="text-left px-5 py-3">Health</th>
                <th className="text-left px-5 py-3">Uptime</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#252836]">
              {activeAgents.map(a => (
                <tr key={a.id} className="hover:bg-white/[0.02]">
                  <td className="px-5 py-2.5 font-medium">{a.name}</td>
                  <td className="px-5 py-2.5"><StatusBadge status={a.status} /></td>
                  <td className="px-5 py-2.5">
                    <div className="flex items-center gap-2 w-28">
                      <div className="flex-1 h-1.5 bg-[#252836] rounded-full">
                        <div className="h-full bg-indigo-500 rounded-full" style={{ width: `${a.cpu}%` }} />
                      </div>
                      <span className="text-[10px] text-slate-500 w-8">{a.cpu}%</span>
                    </div>
                  </td>
                  <td className="px-5 py-2.5 text-xs text-slate-400">{a.memory}MB</td>
                  <td className="px-5 py-2.5">
                    <span className={`text-xs font-semibold ${a.health > 80 ? 'text-emerald-400' : a.health > 50 ? 'text-amber-400' : 'text-red-400'}`}>
                      {a.health}%
                    </span>
                  </td>
                  <td className="px-5 py-2.5 text-xs text-slate-500">{a.uptime}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
