// Simulated agent/system data reflecting the real GhostGoat codebase

export const AGENT_TYPES = {
  WORKER: 'worker',
  SPECIALIST: 'specialist',
  COORDINATOR: 'coordinator',
  MONITOR: 'monitor',
  SELF_EVOLVING: 'self_evolving',
};

export const CAPABILITIES = [
  'CRYPTOGRAPHY', 'MACHINE_LEARNING', 'GRAPH_ANALYSIS',
  'DATA_STRUCTURES', 'MATHEMATICS', 'NETWORKING', 'GENERAL',
  'MARKETING', 'CONTENT_GENERATION', 'SECURITY', 'REASONING',
];

export const SYSTEM_TYPES = [
  'GHOSTGOAT_AGENT', 'NEXUSEVO', 'AUTONOMOUS_AGENT',
  'ORCHESTRATOR', 'ADAP_ENGINE',
];

// All agents discovered in the GhostGoat codebase
export const agents = [
  { id: 'agent-001', name: 'Brain Core', type: AGENT_TYPES.COORDINATOR, status: 'active', health: 98, cpu: 12, memory: 340, capabilities: ['REASONING', 'GENERAL'], module: 'core/reasoning/brain/core.py', tasks_completed: 1247, uptime: '14d 6h' },
  { id: 'agent-002', name: 'LLM Orchestrator', type: AGENT_TYPES.COORDINATOR, status: 'active', health: 95, cpu: 24, memory: 512, capabilities: ['GENERAL', 'MACHINE_LEARNING'], module: 'core/orchestrator/llm_orchestrator.py', tasks_completed: 892, uptime: '14d 6h' },
  { id: 'agent-003', name: 'LLM Powered Orchestrator', type: AGENT_TYPES.COORDINATOR, status: 'active', health: 97, cpu: 31, memory: 680, capabilities: ['GENERAL', 'MACHINE_LEARNING', 'REASONING'], module: 'core/orchestrator/llm_powered_orchestrator.py', tasks_completed: 634, uptime: '7d 2h' },
  { id: 'agent-004', name: 'Integrated Orchestrator', type: AGENT_TYPES.COORDINATOR, status: 'active', health: 92, cpu: 18, memory: 445, capabilities: ['GENERAL'], module: 'core/orchestrator/orchestrator_integration.py', tasks_completed: 423, uptime: '14d 6h' },
  { id: 'agent-005', name: 'Agent Network', type: AGENT_TYPES.WORKER, status: 'active', health: 88, cpu: 8, memory: 210, capabilities: ['NETWORKING'], module: 'core/agents/agent_core/agent_network.py', tasks_completed: 2100, uptime: '14d 6h' },
  { id: 'agent-006', name: 'Cognitive Engine', type: AGENT_TYPES.SPECIALIST, status: 'active', health: 94, cpu: 45, memory: 890, capabilities: ['REASONING', 'MACHINE_LEARNING'], module: 'core/agents/agent_core/cognitive_engine.py', tasks_completed: 3400, uptime: '14d 6h' },
  { id: 'agent-007', name: 'Decision Controller', type: AGENT_TYPES.SPECIALIST, status: 'active', health: 99, cpu: 5, memory: 128, capabilities: ['REASONING'], module: 'core/agents/agent_core/decision_controller.py', tasks_completed: 5600, uptime: '14d 6h' },
  { id: 'agent-008', name: 'Self-Evolving Agent', type: AGENT_TYPES.SELF_EVOLVING, status: 'active', health: 91, cpu: 62, memory: 1200, capabilities: ['MACHINE_LEARNING', 'REASONING', 'GENERAL'], module: 'ACS_SYSTEM/asi/self_evolving_agent.py', tasks_completed: 156, uptime: '3d 11h' },
  { id: 'agent-009', name: 'SmartMoE', type: AGENT_TYPES.SPECIALIST, status: 'active', health: 96, cpu: 38, memory: 720, capabilities: ['CRYPTOGRAPHY', 'MACHINE_LEARNING', 'GRAPH_ANALYSIS', 'MATHEMATICS'], module: 'integrations/smart_moe.py', tasks_completed: 780, uptime: '14d 6h' },
  { id: 'agent-010', name: 'Traversal Agent', type: AGENT_TYPES.WORKER, status: 'idle', health: 100, cpu: 0, memory: 64, capabilities: ['GRAPH_ANALYSIS'], module: 'frameworks/agents/traversal.py', tasks_completed: 340, uptime: '14d 6h' },
  { id: 'agent-011', name: 'Efficiency Engine', type: AGENT_TYPES.MONITOR, status: 'active', health: 97, cpu: 7, memory: 180, capabilities: ['GENERAL'], module: 'core/agents/agent_core/efficiency_engine.py', tasks_completed: 8900, uptime: '14d 6h' },
  { id: 'agent-012', name: 'Content Researcher', type: AGENT_TYPES.SPECIALIST, status: 'idle', health: 100, cpu: 0, memory: 90, capabilities: ['MARKETING', 'CONTENT_GENERATION'], module: 'marketing/Agentic-Ads/backend/rag/agents.py', tasks_completed: 120, uptime: '2d 8h' },
  { id: 'agent-013', name: 'Copywriter Agent', type: AGENT_TYPES.SPECIALIST, status: 'idle', health: 100, cpu: 0, memory: 85, capabilities: ['MARKETING', 'CONTENT_GENERATION'], module: 'marketing/Agentic-Ads/backend/rag/agents.py', tasks_completed: 95, uptime: '2d 8h' },
  { id: 'agent-014', name: 'Visual Designer', type: AGENT_TYPES.SPECIALIST, status: 'offline', health: 0, cpu: 0, memory: 0, capabilities: ['MARKETING', 'CONTENT_GENERATION'], module: 'marketing/Agentic-Ads/backend/rag/agents.py', tasks_completed: 67, uptime: '0' },
  { id: 'agent-015', name: 'Poster Generation Agent', type: AGENT_TYPES.SPECIALIST, status: 'offline', health: 0, cpu: 0, memory: 0, capabilities: ['MARKETING', 'CONTENT_GENERATION'], module: 'marketing/Agentic-Ads/backend/rag/poster_generation.py', tasks_completed: 45, uptime: '0' },
  { id: 'agent-016', name: 'Video/GIF Generator', type: AGENT_TYPES.SPECIALIST, status: 'offline', health: 0, cpu: 0, memory: 0, capabilities: ['MARKETING', 'CONTENT_GENERATION'], module: 'marketing/Agentic-Ads/backend/rag/video_generation.py', tasks_completed: 23, uptime: '0' },
  { id: 'agent-017', name: 'QA Agent', type: AGENT_TYPES.MONITOR, status: 'idle', health: 100, cpu: 0, memory: 70, capabilities: ['GENERAL'], module: 'marketing/Agentic-Ads/backend/rag/agents.py', tasks_completed: 210, uptime: '2d 8h' },
  { id: 'agent-018', name: 'Decision Governor', type: AGENT_TYPES.SPECIALIST, status: 'active', health: 100, cpu: 3, memory: 64, capabilities: ['SECURITY', 'REASONING'], module: 'core/governance/decision_governor.py', tasks_completed: 12400, uptime: '14d 6h' },
  { id: 'agent-019', name: 'Service Registry', type: AGENT_TYPES.WORKER, status: 'active', health: 99, cpu: 2, memory: 48, capabilities: ['GENERAL'], module: 'core/service_registry.py', tasks_completed: 24000, uptime: '14d 6h' },
  { id: 'agent-020', name: 'Dataset Orchestrator', type: AGENT_TYPES.WORKER, status: 'idle', health: 85, cpu: 0, memory: 120, capabilities: ['DATA_STRUCTURES', 'MACHINE_LEARNING'], module: 'applications/empire/motif_dataset_builder.py', tasks_completed: 12, uptime: '1d 4h' },
  { id: 'agent-021', name: 'EvoGoat Agent', type: AGENT_TYPES.SELF_EVOLVING, status: 'active', health: 93, cpu: 55, memory: 950, capabilities: ['MACHINE_LEARNING', 'REASONING', 'GENERAL'], module: 'ACS_SYSTEM/asi/evoagent/agent/main.py', tasks_completed: 89, uptime: '5d 3h' },
];

// Governance policies
export const policies = [
  { id: 'pol-001', name: 'External API Access', scope: 'diagnostic', action: 'allow_external_calls', status: 'enforced', violations: 0 },
  { id: 'pol-002', name: 'Google API Gate', scope: 'google_api', action: 'enforce', status: 'enforced', violations: 2 },
  { id: 'pol-003', name: 'Efficiency Auto-Tune', scope: 'efficiency', action: 'enforce', status: 'enforced', violations: 0 },
  { id: 'pol-004', name: 'Self-Modification Gate', scope: 'asi', action: 'confirm_action', status: 'enforced', violations: 1 },
  { id: 'pol-005', name: 'Agent Spawn Limit', scope: 'orchestrator', action: 'rate_limit', status: 'enforced', violations: 5 },
  { id: 'pol-006', name: 'Memory Write Policy', scope: 'memory', action: 'allow', status: 'permissive', violations: 0 },
];

// System types from unified_integration
export const systems = [
  { id: 'sys-001', name: 'GhostGoat Agent', type: 'GHOSTGOAT_AGENT', status: 'online', agents: 7, tasks: 342 },
  { id: 'sys-002', name: 'NexusEvo', type: 'NEXUSEVO', status: 'online', agents: 2, tasks: 89 },
  { id: 'sys-003', name: 'Autonomous Agent', type: 'AUTONOMOUS_AGENT', status: 'online', agents: 3, tasks: 156 },
  { id: 'sys-004', name: 'Orchestrator', type: 'ORCHESTRATOR', status: 'online', agents: 4, tasks: 634 },
  { id: 'sys-005', name: 'ADAP Engine', type: 'ADAP_ENGINE', status: 'degraded', agents: 5, tasks: 210 },
];

// Task queue
export const generateTasks = () => [
  { id: 'task-001', description: 'Analyze graph connectivity patterns', status: 'running', agent: 'SmartMoE', priority: 8, progress: 67, created: '2m ago' },
  { id: 'task-002', description: 'Train neural embedding model', status: 'running', agent: 'Self-Evolving Agent', priority: 9, progress: 34, created: '15m ago' },
  { id: 'task-003', description: 'Generate marketing copy batch', status: 'queued', agent: null, priority: 5, progress: 0, created: '1m ago' },
  { id: 'task-004', description: 'Validate decision governor policies', status: 'completed', agent: 'Decision Governor', priority: 10, progress: 100, created: '32m ago' },
  { id: 'task-005', description: 'Sync external intelligence feeds', status: 'running', agent: 'Agent Network', priority: 7, progress: 82, created: '5m ago' },
  { id: 'task-006', description: 'Optimize memory vector indices', status: 'queued', agent: null, priority: 6, progress: 0, created: '30s ago' },
  { id: 'task-007', description: 'Run efficiency diagnostics', status: 'completed', agent: 'Efficiency Engine', priority: 4, progress: 100, created: '1h ago' },
  { id: 'task-008', description: 'Deploy poster generation workflow', status: 'failed', agent: 'Poster Generation Agent', priority: 3, progress: 45, created: '20m ago' },
  { id: 'task-009', description: 'Knowledge tank indexing', status: 'running', agent: 'Cognitive Engine', priority: 8, progress: 91, created: '8m ago' },
  { id: 'task-010', description: 'Self-modification safety check', status: 'completed', agent: 'Decision Governor', priority: 10, progress: 100, created: '45m ago' },
];

// Metrics time series (simulated)
export const generateMetrics = () => {
  const now = Date.now();
  const points = 60;
  return Array.from({ length: points }, (_, i) => ({
    time: new Date(now - (points - i) * 60000).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
    cpu: Math.round(20 + Math.sin(i * 0.3) * 15 + Math.random() * 10),
    memory: Math.round(40 + Math.cos(i * 0.2) * 10 + Math.random() * 5),
    tasks: Math.round(8 + Math.sin(i * 0.15) * 5 + Math.random() * 3),
    latency: Math.round(50 + Math.sin(i * 0.4) * 30 + Math.random() * 20),
  }));
};

// Knowledge graph nodes
export const knowledgeNodes = [
  { id: 'k1', label: 'Brain Core', group: 'reasoning', x: 300, y: 200 },
  { id: 'k2', label: 'Memory', group: 'memory', x: 150, y: 100 },
  { id: 'k3', label: 'Optimizer', group: 'reasoning', x: 450, y: 100 },
  { id: 'k4', label: 'Embedding Memory', group: 'memory', x: 100, y: 250 },
  { id: 'k5', label: 'Knowledge Tank', group: 'knowledge', x: 500, y: 250 },
  { id: 'k6', label: 'SmartMoE', group: 'expert', x: 600, y: 150 },
  { id: 'k7', label: 'LLM Orchestrator', group: 'orchestrator', x: 300, y: 350 },
  { id: 'k8', label: 'Agent Network', group: 'network', x: 150, y: 400 },
  { id: 'k9', label: 'Decision Governor', group: 'governance', x: 500, y: 400 },
  { id: 'k10', label: 'Vector Store', group: 'memory', x: 50, y: 300 },
  { id: 'k11', label: 'Cognitive Engine', group: 'reasoning', x: 400, y: 50 },
  { id: 'k12', label: 'Self-Evolving', group: 'asi', x: 200, y: 50 },
  { id: 'k13', label: 'EvoGoat', group: 'asi', x: 100, y: 50 },
  { id: 'k14', label: 'Service Registry', group: 'orchestrator', x: 350, y: 450 },
];

export const knowledgeEdges = [
  { from: 'k1', to: 'k2' }, { from: 'k1', to: 'k3' }, { from: 'k1', to: 'k4' },
  { from: 'k1', to: 'k11' }, { from: 'k2', to: 'k4' }, { from: 'k2', to: 'k10' },
  { from: 'k5', to: 'k6' }, { from: 'k6', to: 'k3' }, { from: 'k7', to: 'k1' },
  { from: 'k7', to: 'k9' }, { from: 'k7', to: 'k8' }, { from: 'k7', to: 'k14' },
  { from: 'k8', to: 'k5' }, { from: 'k9', to: 'k18' }, { from: 'k11', to: 'k6' },
  { from: 'k12', to: 'k1' }, { from: 'k12', to: 'k13' }, { from: 'k13', to: 'k5' },
  { from: 'k14', to: 'k8' },
];

// Communication messages between agents
export const generateMessages = () => [
  { id: 'm1', from: 'LLM Orchestrator', to: 'Brain Core', type: 'task_assign', content: 'Decompose reasoning task #4521', time: '2s ago', status: 'delivered' },
  { id: 'm2', from: 'Brain Core', to: 'Cognitive Engine', type: 'inference', content: 'Run inference chain on context window', time: '5s ago', status: 'delivered' },
  { id: 'm3', from: 'Decision Governor', to: 'Self-Evolving Agent', type: 'policy_check', content: 'Approve self-modification request #89', time: '12s ago', status: 'pending' },
  { id: 'm4', from: 'SmartMoE', to: 'LLM Orchestrator', type: 'result', content: 'Graph analysis complete: 94.2% confidence', time: '18s ago', status: 'delivered' },
  { id: 'm5', from: 'Agent Network', to: 'Service Registry', type: 'heartbeat', content: 'Node health check: all 7 nodes responsive', time: '30s ago', status: 'delivered' },
  { id: 'm6', from: 'Efficiency Engine', to: 'LLM Powered Orchestrator', type: 'alert', content: 'Memory threshold 85% — recommend GC', time: '45s ago', status: 'read' },
  { id: 'm7', from: 'EvoGoat Agent', to: 'Decision Governor', type: 'request', content: 'Request: expand tool registry with web_scrape', time: '1m ago', status: 'pending' },
  { id: 'm8', from: 'Cognitive Engine', to: 'Brain Core', type: 'result', content: 'Inference complete: pattern match score 0.91', time: '1m ago', status: 'delivered' },
];

// Vector memory entries
export const vectorMemoryEntries = [
  { id: 'vec-001', content: 'Graph connectivity analysis yields sparse adjacency matrix', embedding_dim: 768, similarity: 0.94, metadata: { source: 'SmartMoE', domain: 'GRAPH_ANALYSIS' }, timestamp: '2m ago' },
  { id: 'vec-002', content: 'Neural embedding model converged at epoch 47 with loss 0.0023', embedding_dim: 768, similarity: 0.91, metadata: { source: 'Self-Evolving Agent', domain: 'MACHINE_LEARNING' }, timestamp: '15m ago' },
  { id: 'vec-003', content: 'Decision governor approved 99.8% of policy-compliant requests', embedding_dim: 768, similarity: 0.88, metadata: { source: 'Decision Governor', domain: 'SECURITY' }, timestamp: '32m ago' },
  { id: 'vec-004', content: 'Reasoning chain depth-3 reflexion achieved consistency 0.87', embedding_dim: 768, similarity: 0.85, metadata: { source: 'Brain Core', domain: 'REASONING' }, timestamp: '1h ago' },
  { id: 'vec-005', content: 'Agent network latency reduced to avg 12ms after topology optimization', embedding_dim: 768, similarity: 0.82, metadata: { source: 'Agent Network', domain: 'NETWORKING' }, timestamp: '2h ago' },
  { id: 'vec-006', content: 'Marketing copy A/B test: variant B +23% engagement', embedding_dim: 768, similarity: 0.79, metadata: { source: 'Copywriter Agent', domain: 'MARKETING' }, timestamp: '4h ago' },
];
