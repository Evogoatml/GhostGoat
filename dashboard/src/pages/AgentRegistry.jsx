import React, { useState } from 'react';
import { Bot, Search, Filter, ArrowUpDown } from 'lucide-react';
import Card, { CardHeader } from '../components/Card';
import StatusBadge from '../components/StatusBadge';
import { useGhostGoat } from '../HybridContext';
import { AGENT_TYPES } from '../data/agentData';

export default function AgentRegistry() {
  const { agents } = useGhostGoat();
  const [search, setSearch] = useState('');
  const [filterType, setFilterType] = useState('all');
  const [filterStatus, setFilterStatus] = useState('all');
  const [sortBy, setSortBy] = useState('name');
  const [selectedAgent, setSelectedAgent] = useState(null);

  const filtered = agents
    .filter(a => a.name.toLowerCase().includes(search.toLowerCase()))
    .filter(a => filterType === 'all' || a.type === filterType)
    .filter(a => filterStatus === 'all' || a.status === filterStatus)
    .sort((a, b) => {
      if (sortBy === 'name') return a.name.localeCompare(b.name);
      if (sortBy === 'health') return b.health - a.health;
      if (sortBy === 'cpu') return b.cpu - a.cpu;
      if (sortBy === 'tasks') return b.tasks_completed - a.tasks_completed;
      return 0;
    });

  const typeColors = {
    worker: 'text-blue-400', specialist: 'text-purple-400',
    coordinator: 'text-amber-400', monitor: 'text-emerald-400',
    self_evolving: 'text-red-400',
  };

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Agent Registry</h1>
        <p className="text-sm text-slate-400 mt-1">{agents.length} agents registered across {Object.keys(AGENT_TYPES).length} types</p>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-2.5 w-4 h-4 text-slate-500" />
          <input
            type="text" placeholder="Search agents..."
            value={search} onChange={e => setSearch(e.target.value)}
            className="w-full bg-[#1a1d2e] border border-[#252836] rounded-lg pl-10 pr-4 py-2 text-sm text-white placeholder-slate-500 focus:border-indigo-500 focus:outline-none"
          />
        </div>
        <select value={filterType} onChange={e => setFilterType(e.target.value)}
          className="bg-[#1a1d2e] border border-[#252836] rounded-lg px-3 py-2 text-sm text-white focus:border-indigo-500 focus:outline-none">
          <option value="all">All Types</option>
          {Object.entries(AGENT_TYPES).map(([k, v]) => <option key={v} value={v}>{k}</option>)}
        </select>
        <select value={filterStatus} onChange={e => setFilterStatus(e.target.value)}
          className="bg-[#1a1d2e] border border-[#252836] rounded-lg px-3 py-2 text-sm text-white focus:border-indigo-500 focus:outline-none">
          <option value="all">All Statuses</option>
          <option value="active">Active</option>
          <option value="idle">Idle</option>
          <option value="offline">Offline</option>
        </select>
        <select value={sortBy} onChange={e => setSortBy(e.target.value)}
          className="bg-[#1a1d2e] border border-[#252836] rounded-lg px-3 py-2 text-sm text-white focus:border-indigo-500 focus:outline-none">
          <option value="name">Sort: Name</option>
          <option value="health">Sort: Health</option>
          <option value="cpu">Sort: CPU</option>
          <option value="tasks">Sort: Tasks</option>
        </select>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Agent grid */}
        <div className="lg:col-span-2 grid grid-cols-1 md:grid-cols-2 gap-4">
          {filtered.map(agent => (
            <Card key={agent.id} className={`cursor-pointer transition-all hover:border-indigo-500/50 ${selectedAgent?.id === agent.id ? 'border-indigo-500/70 ring-1 ring-indigo-500/30' : ''}`}>
              <div className="p-4" onClick={() => setSelectedAgent(agent)}>
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <Bot className={`w-5 h-5 ${typeColors[agent.type] || 'text-slate-400'}`} />
                    <span className="text-sm font-semibold">{agent.name}</span>
                  </div>
                  <StatusBadge status={agent.status} />
                </div>

                {/* Health bar */}
                <div className="mb-3">
                  <div className="flex justify-between text-[10px] text-slate-500 mb-1">
                    <span>Health</span>
                    <span>{agent.health}%</span>
                  </div>
                  <div className="h-1.5 bg-[#252836] rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-500 ${
                        agent.health > 80 ? 'bg-emerald-500' : agent.health > 50 ? 'bg-amber-500' : 'bg-red-500'
                      }`}
                      style={{ width: `${agent.health}%` }}
                    />
                  </div>
                </div>

                {/* Stats row */}
                <div className="flex items-center gap-4 text-[10px] text-slate-500">
                  <span>CPU: {agent.cpu}%</span>
                  <span>Mem: {agent.memory}MB</span>
                  <span>Tasks: {agent.tasks_completed.toLocaleString()}</span>
                </div>

                {/* Capabilities */}
                <div className="flex flex-wrap gap-1 mt-2">
                  {agent.capabilities.map(cap => (
                    <span key={cap} className="px-1.5 py-0.5 text-[9px] bg-indigo-500/10 text-indigo-300 rounded border border-indigo-500/20">
                      {cap}
                    </span>
                  ))}
                </div>
              </div>
            </Card>
          ))}
        </div>

        {/* Detail panel */}
        <div className="lg:col-span-1">
          {selectedAgent ? (
            <Card>
              <CardHeader icon={Bot} title="Agent Detail" iconColor={typeColors[selectedAgent.type]} />
              <div className="p-5 space-y-4">
                <div>
                  <div className="text-lg font-bold">{selectedAgent.name}</div>
                  <div className="text-xs text-slate-500 mt-1">{selectedAgent.id}</div>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  {[
                    ['Type', selectedAgent.type],
                    ['Status', selectedAgent.status],
                    ['Uptime', selectedAgent.uptime],
                    ['Health', `${selectedAgent.health}%`],
                    ['CPU', `${selectedAgent.cpu}%`],
                    ['Memory', `${selectedAgent.memory}MB`],
                    ['Tasks Done', selectedAgent.tasks_completed.toLocaleString()],
                  ].map(([k, v]) => (
                    <div key={k}>
                      <div className="text-[10px] text-slate-500 uppercase tracking-wider">{k}</div>
                      <div className="text-sm font-medium mt-0.5">{v}</div>
                    </div>
                  ))}
                </div>
                <div>
                  <div className="text-[10px] text-slate-500 uppercase tracking-wider mb-1">Module</div>
                  <div className="text-xs font-mono text-indigo-300 bg-[#0f1117] rounded px-3 py-2 break-all">
                    {selectedAgent.module}
                  </div>
                </div>
                <div>
                  <div className="text-[10px] text-slate-500 uppercase tracking-wider mb-2">Capabilities</div>
                  <div className="flex flex-wrap gap-1">
                    {selectedAgent.capabilities.map(cap => (
                      <span key={cap} className="px-2 py-1 text-xs bg-indigo-500/10 text-indigo-300 rounded border border-indigo-500/20">
                        {cap}
                      </span>
                    ))}
                  </div>
                </div>
                <div className="flex gap-2 pt-2">
                  <button className="flex-1 py-2 text-xs font-medium bg-indigo-600 hover:bg-indigo-700 rounded-lg transition-colors">
                    Restart
                  </button>
                  <button className="flex-1 py-2 text-xs font-medium bg-[#252836] hover:bg-[#2f3347] rounded-lg transition-colors">
                    Pause
                  </button>
                  <button className="flex-1 py-2 text-xs font-medium bg-red-600/20 text-red-400 hover:bg-red-600/30 rounded-lg transition-colors">
                    Stop
                  </button>
                </div>
              </div>
            </Card>
          ) : (
            <Card>
              <div className="p-10 text-center text-slate-500 text-sm">
                <Bot className="w-10 h-10 mx-auto mb-3 opacity-30" />
                Select an agent to view details
              </div>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
