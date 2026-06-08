import React from 'react';
import {
  Bot, ListTodo, Activity, CheckCircle, XCircle, Heart,
  Cpu, Zap,
} from 'lucide-react';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import KPICard from '../components/KPICard';
import Card, { CardHeader } from '../components/Card';
import StatusBadge from '../components/StatusBadge';
import { useGhostGoat } from '../HybridContext';
import { systems } from '../data/agentData';

export default function Overview() {
  const { agents, tasks, chartMetrics: metrics, messages, stats, systemMetrics, backendOnline } = useGhostGoat();

  return (
    <div className="p-6 space-y-6">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold">Multi-Agent Command Center</h1>
        <p className="text-sm text-slate-400 mt-1">Real-time overview of all GhostGoat subsystems</p>
      </div>

      {/* KPI Strip */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        <KPICard icon={Bot} label="Active Agents" value={stats.activeAgents} sub={`of ${stats.totalAgents} total`} color="indigo" />
        <KPICard icon={ListTodo} label="Running Tasks" value={stats.runningTasks} sub={`${stats.totalTasks} total`} color="amber" />
        <KPICard icon={CheckCircle} label="Completed" value={stats.completedTasks} color="emerald" />
        <KPICard icon={XCircle} label="Failed" value={stats.failedTasks} color="red" />
        <KPICard icon={Heart} label="Avg Health" value={`${stats.avgHealth}%`} color="purple" />
        <KPICard icon={Cpu} label="CPU" value={systemMetrics ? `${systemMetrics.cpu_percent}%` : `${stats.totalCpu}%`} sub={systemMetrics ? 'real' : 'sim'} color="blue" />
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader icon={Activity} title="CPU & Memory (60m)" iconColor="text-emerald-400" />
          <div className="p-4 h-64">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={metrics}>
                <defs>
                  <linearGradient id="cpuGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="memGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <XAxis dataKey="time" tick={{ fontSize: 10, fill: '#64748b' }} interval={9} />
                <YAxis tick={{ fontSize: 10, fill: '#64748b' }} domain={[0, 100]} />
                <Tooltip contentStyle={{ background: '#1a1d2e', border: '1px solid #252836', borderRadius: 8, fontSize: 12 }} />
                <Area type="monotone" dataKey="cpu" stroke="#6366f1" fill="url(#cpuGrad)" strokeWidth={2} name="CPU %" />
                <Area type="monotone" dataKey="memory" stroke="#10b981" fill="url(#memGrad)" strokeWidth={2} name="Mem %" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </Card>

        <Card>
          <CardHeader icon={Zap} title="Task Throughput & Latency" iconColor="text-amber-400" />
          <div className="p-4 h-64">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={metrics}>
                <defs>
                  <linearGradient id="taskGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#f59e0b" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="latGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <XAxis dataKey="time" tick={{ fontSize: 10, fill: '#64748b' }} interval={9} />
                <YAxis tick={{ fontSize: 10, fill: '#64748b' }} />
                <Tooltip contentStyle={{ background: '#1a1d2e', border: '1px solid #252836', borderRadius: 8, fontSize: 12 }} />
                <Area type="monotone" dataKey="tasks" stroke="#f59e0b" fill="url(#taskGrad)" strokeWidth={2} name="Tasks/min" />
                <Area type="monotone" dataKey="latency" stroke="#ef4444" fill="url(#latGrad)" strokeWidth={2} name="Latency ms" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>

      {/* Bottom row: systems + recent activity */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Systems */}
        <Card>
          <CardHeader icon={Activity} title="Subsystems" iconColor="text-purple-400" />
          <div className="divide-y divide-[#252836]">
            {systems.map(sys => (
              <div key={sys.id} className="flex items-center justify-between px-5 py-3">
                <div>
                  <div className="text-sm font-medium">{sys.name}</div>
                  <div className="text-xs text-slate-500">{sys.type}</div>
                </div>
                <div className="flex items-center gap-4">
                  <span className="text-xs text-slate-400">{sys.agents} agents</span>
                  <span className="text-xs text-slate-400">{sys.tasks} tasks</span>
                  <StatusBadge status={sys.status} />
                </div>
              </div>
            ))}
          </div>
        </Card>

        {/* Recent messages */}
        <Card>
          <CardHeader icon={Zap} title="Live Agent Messages" iconColor="text-cyan-400" />
          <div className="divide-y divide-[#252836] max-h-72 overflow-y-auto">
            {messages.map(msg => (
              <div key={msg.id} className="px-5 py-3">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs font-semibold text-indigo-400">{msg.from}</span>
                  <span className="text-xs text-slate-600">&rarr;</span>
                  <span className="text-xs font-semibold text-purple-400">{msg.to}</span>
                  <StatusBadge status={msg.status} />
                  <span className="ml-auto text-[10px] text-slate-500">{msg.time}</span>
                </div>
                <div className="text-xs text-slate-400">{msg.content}</div>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}
