/**
 * Hybrid data provider.
 * When backend is online: uses real data from API.
 * When backend is offline: uses simulated data.
 * Dashboard pages don't care which — same interface either way.
 */
import { useHybridData } from './useApi';
import { useSimulation } from './useSimulation';

export function useHybrid() {
  const api = useHybridData();
  const sim = useSimulation();

  const online = api.backendOnline;

  // Merge agents: real if available, simulated fallback
  const agents = online && api.agents.length > 0 ? api.agents : sim.agents;
  const tasks = online && api.tasks.length > 0 ? api.tasks : sim.tasks;
  const messages = online && api.messages.length > 0 ? api.messages : sim.messages;
  const policies = online && api.policies.policies?.length > 0 ? api.policies : {
    policies: [
      { id: 'pol-001', name: 'External API Access', scope: 'diagnostic', status: 'enforced', violations: 0 },
      { id: 'pol-002', name: 'Google API Gate', scope: 'google_api', status: 'enforced', violations: 2 },
      { id: 'pol-003', name: 'Self-Modification Gate', scope: 'asi', status: 'enforced', violations: 1 },
    ],
    audit_log: [],
  };

  // Metrics: real system metrics when available, simulated chart data always
  const systemMetrics = online ? api.metrics : null;
  const chartMetrics = sim.metrics; // always simulated for 60m chart (real only gives one point)

  // Compute stats from whichever source we're using
  const activeAgents = agents.filter(a => a.status === 'active').length;
  const runningTasks = tasks.filter(t => t.status === 'running').length;
  const completedTasks = tasks.filter(t => t.status === 'completed').length;
  const failedTasks = tasks.filter(t => t.status === 'failed').length;

  return {
    // Connection state
    backendOnline: online,
    health: api.health,

    // Data (real or simulated)
    agents,
    tasks,
    messages,
    policies,
    systemMetrics,
    chartMetrics,
    services: api.services,

    // Computed stats
    stats: {
      activeAgents,
      totalAgents: agents.length,
      runningTasks,
      completedTasks,
      failedTasks,
      totalTasks: tasks.length,
      avgHealth: online && api.health
        ? 100 // real = healthy if connected
        : sim.stats.avgHealth,
      totalCpu: systemMetrics?.cpu_percent ?? sim.stats.totalCpu,
    },

    // Actions (only work when backend online)
    submitTask: api.submitTask,
    sendMessage: api.sendMessage,
    searchKnowledge: api.searchKnowledge,
  };
}
