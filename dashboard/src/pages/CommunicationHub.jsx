import React, { useState } from 'react';
import { MessageSquare, Send, Filter } from 'lucide-react';
import Card, { CardHeader } from '../components/Card';
import StatusBadge from '../components/StatusBadge';
import { useGhostGoat } from '../HybridContext';

const messageTypes = {
  task_assign: { color: 'text-indigo-400', bg: 'bg-indigo-500/10', label: 'TASK' },
  inference: { color: 'text-purple-400', bg: 'bg-purple-500/10', label: 'INFERENCE' },
  policy_check: { color: 'text-amber-400', bg: 'bg-amber-500/10', label: 'POLICY' },
  result: { color: 'text-emerald-400', bg: 'bg-emerald-500/10', label: 'RESULT' },
  heartbeat: { color: 'text-cyan-400', bg: 'bg-cyan-500/10', label: 'HEARTBEAT' },
  alert: { color: 'text-red-400', bg: 'bg-red-500/10', label: 'ALERT' },
  request: { color: 'text-blue-400', bg: 'bg-blue-500/10', label: 'REQUEST' },
};

export default function CommunicationHub() {
  const { messages, agents, sendMessage: apiSendMessage, backendOnline } = useGhostGoat();
  const [filterType, setFilterType] = useState('all');
  const [newMessage, setNewMessage] = useState('');
  const [fromAgent, setFromAgent] = useState('');
  const [toAgent, setToAgent] = useState('');

  const filtered = filterType === 'all'
    ? messages
    : messages.filter(m => m.type === filterType);

  const activeAgents = agents.filter(a => a.status !== 'offline');

  // Build adjacency for the flow diagram
  const flows = {};
  messages.forEach(m => {
    const key = `${m.from}->${m.to}`;
    flows[key] = (flows[key] || 0) + 1;
  });

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Communication Hub</h1>
        <p className="text-sm text-slate-400 mt-1">Inter-agent message flows and communication channels</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Message stream */}
        <div className="lg:col-span-2 space-y-4">
          {/* Filter */}
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => setFilterType('all')}
              className={`px-3 py-1.5 text-xs font-medium rounded-lg border transition-colors ${
                filterType === 'all' ? 'bg-indigo-600/20 border-indigo-500/30 text-indigo-300' : 'bg-[#1a1d2e] border-[#252836] text-slate-400 hover:text-white'
              }`}
            >
              All
            </button>
            {Object.entries(messageTypes).map(([type, { label, color }]) => (
              <button
                key={type}
                onClick={() => setFilterType(type)}
                className={`px-3 py-1.5 text-xs font-medium rounded-lg border transition-colors ${
                  filterType === type ? 'bg-indigo-600/20 border-indigo-500/30 text-indigo-300' : 'bg-[#1a1d2e] border-[#252836] text-slate-400 hover:text-white'
                }`}
              >
                {label}
              </button>
            ))}
          </div>

          {/* Messages */}
          <Card>
            <CardHeader icon={MessageSquare} title="Message Stream" iconColor="text-cyan-400">
              <span className="text-xs text-slate-500">{filtered.length} messages</span>
            </CardHeader>
            <div className="divide-y divide-[#252836] max-h-[500px] overflow-y-auto">
              {filtered.map(msg => {
                const mt = messageTypes[msg.type] || messageTypes.result;
                return (
                  <div key={msg.id} className="px-5 py-4 hover:bg-white/[0.02] transition-colors">
                    <div className="flex items-center gap-2 mb-2">
                      <span className={`px-1.5 py-0.5 text-[10px] font-bold rounded ${mt.bg} ${mt.color}`}>
                        {mt.label}
                      </span>
                      <span className="text-xs font-semibold text-indigo-400">{msg.from}</span>
                      <span className="text-slate-600">&rarr;</span>
                      <span className="text-xs font-semibold text-purple-400">{msg.to}</span>
                      <StatusBadge status={msg.status} />
                      <span className="ml-auto text-[10px] text-slate-500">{msg.time}</span>
                    </div>
                    <div className="text-sm text-slate-300 ml-1">{msg.content}</div>
                  </div>
                );
              })}
            </div>
          </Card>

          {/* Send message */}
          <Card>
            <div className="p-4">
              <div className="flex gap-3 mb-3">
                <select value={fromAgent} onChange={e => setFromAgent(e.target.value)}
                  className="flex-1 bg-[#0f1117] border border-[#252836] rounded-lg px-3 py-2 text-xs text-white focus:border-indigo-500 focus:outline-none">
                  <option value="">From agent...</option>
                  {activeAgents.map(a => <option key={a.id} value={a.name}>{a.name}</option>)}
                </select>
                <select value={toAgent} onChange={e => setToAgent(e.target.value)}
                  className="flex-1 bg-[#0f1117] border border-[#252836] rounded-lg px-3 py-2 text-xs text-white focus:border-indigo-500 focus:outline-none">
                  <option value="">To agent...</option>
                  {activeAgents.map(a => <option key={a.id} value={a.name}>{a.name}</option>)}
                </select>
              </div>
              <div className="flex gap-2">
                <input
                  type="text" placeholder="Type a message..."
                  value={newMessage} onChange={e => setNewMessage(e.target.value)}
                  className="flex-1 bg-[#0f1117] border border-[#252836] rounded-lg px-4 py-2 text-sm text-white placeholder-slate-500 focus:border-indigo-500 focus:outline-none"
                />
                <button className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 rounded-lg transition-colors flex items-center gap-2 text-sm font-medium">
                  <Send className="w-4 h-4" /> Send
                </button>
              </div>
            </div>
          </Card>
        </div>

        {/* Flow summary */}
        <div className="lg:col-span-1 space-y-4">
          <Card>
            <CardHeader icon={Filter} title="Active Flows" iconColor="text-purple-400" />
            <div className="divide-y divide-[#252836] max-h-80 overflow-y-auto">
              {Object.entries(flows).map(([flow, count]) => {
                const [from, to] = flow.split('->');
                return (
                  <div key={flow} className="px-5 py-3">
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-indigo-400 font-medium">{from}</span>
                      <span className="text-slate-600">&rarr;</span>
                      <span className="text-xs text-purple-400 font-medium">{to}</span>
                      <span className="ml-auto text-xs font-bold text-white bg-[#252836] px-2 py-0.5 rounded">
                        {count}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </Card>

          {/* Channel stats */}
          <Card>
            <CardHeader icon={MessageSquare} title="Channel Stats" iconColor="text-emerald-400" />
            <div className="p-5 space-y-3">
              {Object.entries(messageTypes).map(([type, { label, color, bg }]) => {
                const count = messages.filter(m => m.type === type).length;
                return (
                  <div key={type} className="flex items-center justify-between">
                    <span className={`text-xs ${color}`}>{label}</span>
                    <div className="flex items-center gap-2">
                      <div className="w-20 h-1.5 bg-[#252836] rounded-full">
                        <div className={`h-full rounded-full ${bg.replace('/10', '/40')}`}
                          style={{ width: `${(count / messages.length) * 100}%` }} />
                      </div>
                      <span className="text-xs text-slate-400 w-4">{count}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
