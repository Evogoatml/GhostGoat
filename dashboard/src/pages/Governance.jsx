import React, { useState } from 'react';
import { Shield, AlertTriangle, CheckCircle, Lock, Eye } from 'lucide-react';
import Card, { CardHeader } from '../components/Card';
import StatusBadge from '../components/StatusBadge';
import KPICard from '../components/KPICard';
import { useGhostGoat } from '../HybridContext';
import { policies as samplePolicies } from '../data/agentData';

const sampleAuditLog = [
  { time: 'demo', event: 'Policy Check', agent: 'Sample Agent', policy: 'External Task Execution', result: 'allowed', detail: 'Example only; not a recorded event' },
];

export default function Governance() {
  const { backendOnline, policies: liveGovernance, checkPolicy } = useGhostGoat();
  const [selectedPolicy, setSelectedPolicy] = useState(null);
  const [checkResult, setCheckResult] = useState(null);
  const policies = backendOnline ? liveGovernance.policies : samplePolicies;
  const auditLog = backendOnline ? liveGovernance.audit_log : sampleAuditLog;
  const totalViolations = policies.reduce((sum, policy) => sum + (policy.violations || 0), 0);
  const enforced = policies.filter(policy => policy.status === 'enforced').length;

  const runCheck = async () => {
    const result = await checkPolicy();
    setCheckResult(result.error || result.result);
  };

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Governance & Policy</h1>
        <p className="text-sm text-slate-400 mt-1">
          {backendOnline ? 'Live task-execution policy and recorded checks' : 'Simulated policy examples — connect the API for live governance'}
        </p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <KPICard icon={Shield} label="Policies" value={policies.length} color="indigo" />
        <KPICard icon={Lock} label="Enforced" value={enforced} color="emerald" />
        <KPICard icon={AlertTriangle} label="Blocked Checks" value={totalViolations} color="amber" />
        <KPICard icon={CheckCircle} label="Policy Checks" value={auditLog.length} color="purple" />
      </div>

      {backendOnline && (
        <Card>
          <div className="p-4 flex items-center gap-3">
            <button onClick={runCheck} className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 rounded-lg text-sm">
              Check task execution policy
            </button>
            {checkResult && <span className="text-sm text-slate-300">Latest check: {checkResult}</span>}
          </div>
        </Card>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1 space-y-3">
          <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider">Policies</h3>
          {policies.map(policy => (
            <Card key={policy.id} className="cursor-pointer transition-all hover:border-indigo-500/50">
              <div className="p-4" onClick={() => setSelectedPolicy(policy)}>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium">{policy.name}</span>
                  <StatusBadge status={policy.status} />
                </div>
                <div className="flex items-center gap-3 text-[10px] text-slate-500">
                  <span>Scope: {policy.scope}</span>
                  <span>Action: {policy.action}</span>
                  {policy.allowed !== undefined && <span>Decision: {policy.allowed ? 'allowed' : 'blocked'}</span>}
                  {policy.violations > 0 && <span className="text-amber-400">{policy.violations} blocked</span>}
                </div>
                {selectedPolicy?.id === policy.id && (
                  <p className="mt-2 text-xs text-slate-400">Policy is evaluated by the API before analyst requests.</p>
                )}
              </div>
            </Card>
          ))}
          {!policies.length && <p className="text-sm text-slate-500">No governance provider is available.</p>}
        </div>

        <div className="lg:col-span-2">
          <Card>
            <CardHeader icon={Eye} title="Audit Trail" iconColor="text-cyan-400" />
            <div className="divide-y divide-[#252836] max-h-[600px] overflow-y-auto">
              {auditLog.map((entry, index) => {
                const decision = entry.result === 'allowed' || entry.result === 'approved';
                return (
                  <div key={`${entry.time}-${index}`} className="px-5 py-3 hover:bg-white/[0.02]">
                    <div className="flex items-center gap-3 mb-1">
                      <span className={`w-2 h-2 rounded-full flex-shrink-0 ${decision ? 'bg-emerald-400' : 'bg-red-400'}`} />
                      <span className="text-sm font-medium text-white">{entry.event}</span>
                      <span className={`text-xs font-medium px-1.5 py-0.5 rounded ${decision ? 'bg-emerald-500/10 text-emerald-400' : 'bg-red-500/10 text-red-400'}`}>
                        {entry.result}
                      </span>
                      <span className="ml-auto text-[10px] text-slate-500">{entry.time}</span>
                    </div>
                    <div className="flex items-center gap-2 text-xs text-slate-400 ml-5">
                      <span className="text-indigo-400">{entry.agent || 'API'}</span>
                      <span className="text-slate-600">/</span>
                      <span className="text-purple-400">{entry.policy || entry.context}</span>
                    </div>
                    <div className="text-xs text-slate-500 ml-5 mt-1">{entry.detail || entry.context}</div>
                  </div>
                );
              })}
              {!auditLog.length && <p className="p-5 text-sm text-slate-500">No policy checks have been recorded.</p>}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
