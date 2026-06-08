import React, { useState } from 'react';
import { Shield, AlertTriangle, CheckCircle, Lock, Eye } from 'lucide-react';
import Card, { CardHeader } from '../components/Card';
import StatusBadge from '../components/StatusBadge';
import KPICard from '../components/KPICard';
import { policies } from '../data/agentData';

export default function Governance() {
  const [selectedPolicy, setSelectedPolicy] = useState(null);

  const totalViolations = policies.reduce((s, p) => s + p.violations, 0);
  const enforced = policies.filter(p => p.status === 'enforced').length;

  // Simulated audit log
  const auditLog = [
    { time: '12s ago', event: 'Policy Check', agent: 'Self-Evolving Agent', policy: 'Self-Modification Gate', result: 'approved', detail: 'Modification within safety bounds' },
    { time: '45s ago', event: 'Rate Limit Hit', agent: 'LLM Orchestrator', policy: 'Agent Spawn Limit', result: 'blocked', detail: 'Exceeded 10 spawns/min threshold' },
    { time: '2m ago', event: 'API Access', agent: 'Agent Network', policy: 'External API Access', result: 'approved', detail: 'Diagnostic context approved' },
    { time: '5m ago', event: 'Policy Check', agent: 'EvoGoat Agent', policy: 'Self-Modification Gate', result: 'pending', detail: 'Awaiting human review: expand tool registry' },
    { time: '12m ago', event: 'Google API Call', agent: 'Task Handler', policy: 'Google API Gate', result: 'approved', detail: 'Standard API operation' },
    { time: '18m ago', event: 'Rate Limit Hit', agent: 'LLM Powered Orchestrator', policy: 'Agent Spawn Limit', result: 'blocked', detail: 'Burst creation throttled' },
    { time: '30m ago', event: 'Memory Write', agent: 'Cognitive Engine', policy: 'Memory Write Policy', result: 'approved', detail: 'Permissive mode: auto-approve' },
    { time: '1h ago', event: 'Self-Modify Request', agent: 'Self-Evolving Agent', policy: 'Self-Modification Gate', result: 'blocked', detail: 'Recursive depth exceeded safety margin' },
  ];

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Governance & Policy</h1>
        <p className="text-sm text-slate-400 mt-1">Decision governor, security policies, and audit trail</p>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <KPICard icon={Shield} label="Active Policies" value={policies.length} color="indigo" />
        <KPICard icon={Lock} label="Enforced" value={enforced} color="emerald" />
        <KPICard icon={AlertTriangle} label="Total Violations" value={totalViolations} color="amber" />
        <KPICard icon={CheckCircle} label="Compliance" value={`${Math.round((1 - totalViolations / 100) * 100)}%`} color="purple" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Policy list */}
        <div className="lg:col-span-1 space-y-3">
          <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider">Policies</h3>
          {policies.map(policy => (
            <Card
              key={policy.id}
              className={`cursor-pointer transition-all hover:border-indigo-500/50 ${selectedPolicy?.id === policy.id ? 'border-indigo-500/70 ring-1 ring-indigo-500/30' : ''}`}
            >
              <div className="p-4" onClick={() => setSelectedPolicy(policy)}>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium">{policy.name}</span>
                  <StatusBadge status={policy.status} />
                </div>
                <div className="flex items-center gap-3 text-[10px] text-slate-500">
                  <span>Scope: {policy.scope}</span>
                  <span>Action: {policy.action}</span>
                  {policy.violations > 0 && (
                    <span className="text-amber-400">{policy.violations} violations</span>
                  )}
                </div>
              </div>
            </Card>
          ))}
        </div>

        {/* Audit log */}
        <div className="lg:col-span-2">
          <Card>
            <CardHeader icon={Eye} title="Audit Trail" iconColor="text-cyan-400" />
            <div className="divide-y divide-[#252836] max-h-[600px] overflow-y-auto">
              {auditLog.map((entry, i) => (
                <div key={i} className="px-5 py-3 hover:bg-white/[0.02]">
                  <div className="flex items-center gap-3 mb-1">
                    <span className={`w-2 h-2 rounded-full flex-shrink-0 ${
                      entry.result === 'approved' ? 'bg-emerald-400' :
                      entry.result === 'blocked' ? 'bg-red-400' : 'bg-amber-400'
                    }`} />
                    <span className="text-sm font-medium text-white">{entry.event}</span>
                    <span className={`text-xs font-medium px-1.5 py-0.5 rounded ${
                      entry.result === 'approved' ? 'bg-emerald-500/10 text-emerald-400' :
                      entry.result === 'blocked' ? 'bg-red-500/10 text-red-400' : 'bg-amber-500/10 text-amber-400'
                    }`}>
                      {entry.result}
                    </span>
                    <span className="ml-auto text-[10px] text-slate-500">{entry.time}</span>
                  </div>
                  <div className="flex items-center gap-2 text-xs text-slate-400 ml-5">
                    <span className="text-indigo-400">{entry.agent}</span>
                    <span className="text-slate-600">/</span>
                    <span className="text-purple-400">{entry.policy}</span>
                  </div>
                  <div className="text-xs text-slate-500 ml-5 mt-1">{entry.detail}</div>
                </div>
              ))}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
