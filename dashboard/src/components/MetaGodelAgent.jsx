import React, { useState, useEffect, useRef } from 'react';
import { Play, Pause, StopCircle, Database, Brain, Network, Activity, GitBranch, Zap } from 'lucide-react';

const MetaGodelAgent = () => {
  const [agentState, setAgentState] = useState('idle');
  const [logs, setLogs] = useState([]);
  const [graphState, setGraphState] = useState({});
  const [vectorMemory, setVectorMemory] = useState([]);
  const [currentTask, setCurrentTask] = useState('');
  const [reflexionDepth, setReflexionDepth] = useState(0);
  const [consistencyScore, setConsistencyScore] = useState(0);
  const [semanticRoute, setSemanticRoute] = useState('');
  const canvasRef = useRef(null);
  const [taskInput, setTaskInput] = useState('');

  // GraphRAG Vector Store simulation
  class GraphRAGStore {
    constructor() {
      this.nodes = new Map();
      this.edges = new Map();
      this.embeddings = new Map();
      this.communityStructure = new Map();
    }

    async addNode(id, content, metadata = {}) {
      const embedding = this.generateEmbedding(content);
      this.nodes.set(id, {
        content,
        metadata,
        embedding,
        timestamp: Date.now()
      });
      this.updateCommunityStructure(id, embedding);
      return id;
    }

    generateEmbedding(text) {
      // Simulated semantic embedding
      const hash = text.split('').reduce((acc, char) => {
        return ((acc << 5) - acc) + char.charCodeAt(0);
      }, 0);

      const dim = 8;
      const embedding = new Array(dim).fill(0).map((_, i) =>
        Math.sin(hash * (i + 1) * 0.01) * 0.5 + 0.5
      );

      return embedding;
    }

    updateCommunityStructure(nodeId, embedding) {
      let assignedCommunity = 0;
      let maxSimilarity = -1;

      for (const [commId, centroid] of this.communityStructure.entries()) {
        const similarity = this.cosineSimilarity(embedding, centroid);
        if (similarity > maxSimilarity) {
          maxSimilarity = similarity;
          assignedCommunity = commId;
        }
      }

      if (maxSimilarity < 0.5 || this.communityStructure.size === 0) {
        assignedCommunity = this.communityStructure.size;
        this.communityStructure.set(assignedCommunity, embedding);
      }

      const node = this.nodes.get(nodeId);
      if (node) {
        node.metadata.communityId = assignedCommunity;
      }
    }

    cosineSimilarity(a, b) {
      const dotProduct = a.reduce((sum, val, i) => sum + val * b[i], 0);
      const magnitudeA = Math.sqrt(a.reduce((sum, val) => sum + val * val, 0));
      const magnitudeB = Math.sqrt(b.reduce((sum, val) => sum + val * val, 0));
      return dotProduct / (magnitudeA * magnitudeB);
    }

    similaritySearch(query, k = 5) {
      const queryEmbedding = this.generateEmbedding(query);
      const results = [];

      for (const [id, node] of this.nodes.entries()) {
        const similarity = this.cosineSimilarity(queryEmbedding, node.embedding);
        results.push({ id, node, similarity });
      }

      return results
        .sort((a, b) => b.similarity - a.similarity)
        .slice(0, k);
    }
  }

  // Semantic Router
  const semanticRoutes = {
    'analytical_reasoning': ['analyze', 'calculate', 'evaluate', 'measure'],
    'creative_synthesis': ['generate', 'create', 'brainstorm', 'ideate'],
    'meta_cognitive_reflection': ['reflect', 'evaluate reasoning', 'check consistency'],
    'tool_orchestration': ['execute', 'run', 'orchestrate', 'coordinate'],
    'knowledge_integration': ['integrate', 'connect', 'synthesize', 'combine']
  };

  const routeTask = (task) => {
    const taskLower = task.toLowerCase();

    for (const [route, keywords] of Object.entries(semanticRoutes)) {
      if (keywords.some(kw => taskLower.includes(kw))) {
        return route;
      }
    }

    return 'general_reasoning';
  };

  // Neuro-ReAct Agent
  const executeReActCycle = async (task) => {
    const steps = [];

    // Thought
    steps.push({
      type: 'thought',
      content: `Analyzing task: "${task}". Need to determine optimal approach based on semantic route: ${semanticRoute}`
    });

    // Action
    const action = semanticRoute === 'analytical_reasoning'
      ? 'Query vector database for relevant context'
      : 'Generate novel solution approach';

    steps.push({
      type: 'action',
      content: action
    });

    // Observation
    steps.push({
      type: 'observation',
      content: `Action completed. Retrieved ${Math.floor(Math.random() * 10) + 1} relevant memory chunks.`
    });

    return steps;
  };

  // Execute task
  const executeTask = async () => {
    if (!taskInput.trim()) return;

    setAgentState('running');
    setCurrentTask(taskInput);
    setLogs([]);
    setReflexionDepth(0);

    addLog('🚀 Initializing Meta-Gödel Agent...');

    // Route task
    const route = routeTask(taskInput);
    setSemanticRoute(route);
    addLog(`🧭 Semantic Route: ${route}`);

    await sleep(500);

    // Retrieve context from GraphRAG
    addLog('🔍 Retrieving context from GraphRAG...');
    const graphStore = new GraphRAGStore();

    // Simulate adding knowledge
    await graphStore.addNode('node_1', taskInput, { type: 'task' });
    await graphStore.addNode('node_2', 'Related context about autonomous systems', { type: 'context' });

    const retrievedContext = graphStore.similaritySearch(taskInput, 3);
    addLog(`📊 Retrieved ${retrievedContext.length} relevant nodes`);

    await sleep(500);

    // Execute ReAct cycle
    addLog('🧠 Executing Neuro-ReAct reasoning cycle...');
    const reactSteps = await executeReActCycle(taskInput);

    for (const step of reactSteps) {
      addLog(`  ${step.type.toUpperCase()}: ${step.content}`);
      await sleep(300);
    }

    // Meta-cognitive reflection
    addLog('🔄 Entering meta-cognitive reflection...');
    await sleep(500);

    for (let depth = 0; depth < 3; depth++) {
      setReflexionDepth(depth + 1);

      const score = 0.5 + (depth * 0.15) + (Math.random() * 0.1);
      setConsistencyScore(Math.min(score, 1.0));

      addLog(`  Reflexion depth ${depth + 1}: Consistency score = ${score.toFixed(3)}`);
      await sleep(400);

      if (score > 0.8) {
        addLog('  ✓ High consistency achieved, finalizing...');
        break;
      }
    }

    // Update memory
    addLog('💾 Updating vector memory and knowledge graph...');
    setVectorMemory(prev => [...prev, {
      task: taskInput,
      route: route,
      timestamp: new Date().toISOString(),
      consistency: consistencyScore
    }]);

    await sleep(500);

    addLog('✅ Task execution complete!');
    setAgentState('complete');
  };

  const addLog = (message) => {
    setLogs(prev => [...prev, {
      timestamp: new Date().toISOString(),
      message
    }]);
  };

  const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));

  const resetAgent = () => {
    setAgentState('idle');
    setLogs([]);
    setCurrentTask('');
    setReflexionDepth(0);
    setConsistencyScore(0);
    setSemanticRoute('');
    setTaskInput('');
  };

  // Draw knowledge graph visualization
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    const width = canvas.width;
    const height = canvas.height;

    ctx.clearRect(0, 0, width, height);

    // Draw nodes
    const numNodes = Math.min(vectorMemory.length + 3, 10);
    const nodes = [];

    for (let i = 0; i < numNodes; i++) {
      const angle = (i / numNodes) * Math.PI * 2;
      const radius = 100;
      const x = width / 2 + Math.cos(angle) * radius;
      const y = height / 2 + Math.sin(angle) * radius;

      nodes.push({ x, y });

      // Draw node
      ctx.beginPath();
      ctx.arc(x, y, 8, 0, Math.PI * 2);
      ctx.fillStyle = i < vectorMemory.length ? '#3b82f6' : '#6b7280';
      ctx.fill();
      ctx.strokeStyle = '#1e40af';
      ctx.lineWidth = 2;
      ctx.stroke();
    }

    // Draw edges
    ctx.strokeStyle = '#60a5fa';
    ctx.lineWidth = 1;
    ctx.globalAlpha = 0.3;

    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        if (Math.random() > 0.6) {
          ctx.beginPath();
          ctx.moveTo(nodes[i].x, nodes[i].y);
          ctx.lineTo(nodes[j].x, nodes[j].y);
          ctx.stroke();
        }
      }
    }

    ctx.globalAlpha = 1.0;

  }, [vectorMemory, agentState]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-blue-900 to-slate-900 p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-white mb-2">
            Meta-Agentic Gödel Agent System
          </h1>
          <p className="text-blue-300">
            LangGraph &bull; GraphRAG &bull; Neuro-ReAct &bull; Semantic Router &bull; Databricks Integration
          </p>
        </div>

        {/* Main Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Control Panel */}
          <div className="lg:col-span-1 space-y-6">
            {/* Task Input */}
            <div className="bg-slate-800 rounded-lg p-6 border border-blue-500/30">
              <h2 className="text-xl font-semibold text-white mb-4 flex items-center gap-2">
                <Zap className="w-5 h-5 text-yellow-400" />
                Task Input
              </h2>

              <textarea
                value={taskInput}
                onChange={(e) => setTaskInput(e.target.value)}
                placeholder="Enter task to analyze (e.g., 'Analyze customer churn patterns using distributed SQL')"
                className="w-full h-32 bg-slate-900 text-white rounded p-3 border border-slate-700 focus:border-blue-500 focus:outline-none resize-none"
                disabled={agentState === 'running'}
              />

              <div className="flex gap-3 mt-4">
                <button
                  onClick={executeTask}
                  disabled={agentState === 'running' || !taskInput.trim()}
                  className="flex-1 flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-600 text-white py-3 rounded font-semibold transition-colors"
                >
                  <Play className="w-4 h-4" />
                  Execute
                </button>

                <button
                  onClick={resetAgent}
                  className="flex items-center justify-center gap-2 bg-slate-700 hover:bg-slate-600 text-white px-4 py-3 rounded font-semibold transition-colors"
                >
                  <StopCircle className="w-4 h-4" />
                  Reset
                </button>
              </div>
            </div>

            {/* Agent State */}
            <div className="bg-slate-800 rounded-lg p-6 border border-blue-500/30">
              <h2 className="text-xl font-semibold text-white mb-4 flex items-center gap-2">
                <Activity className="w-5 h-5 text-green-400" />
                Agent State
              </h2>

              <div className="space-y-3">
                <div>
                  <div className="text-sm text-slate-400 mb-1">Status</div>
                  <div className={`text-lg font-semibold ${
                    agentState === 'idle' ? 'text-slate-400' :
                    agentState === 'running' ? 'text-yellow-400' :
                    'text-green-400'
                  }`}>
                    {agentState.toUpperCase()}
                  </div>
                </div>

                <div>
                  <div className="text-sm text-slate-400 mb-1">Semantic Route</div>
                  <div className="text-white font-mono text-sm bg-slate-900 px-3 py-2 rounded">
                    {semanticRoute || 'None'}
                  </div>
                </div>

                <div>
                  <div className="text-sm text-slate-400 mb-1">Reflexion Depth</div>
                  <div className="flex items-center gap-2">
                    <div className="flex-1 bg-slate-700 rounded-full h-2">
                      <div
                        className="bg-blue-500 h-2 rounded-full transition-all duration-300"
                        style={{ width: `${(reflexionDepth / 3) * 100}%` }}
                      />
                    </div>
                    <span className="text-white font-semibold w-8">{reflexionDepth}/3</span>
                  </div>
                </div>

                <div>
                  <div className="text-sm text-slate-400 mb-1">Self-Consistency Score</div>
                  <div className="flex items-center gap-2">
                    <div className="flex-1 bg-slate-700 rounded-full h-2">
                      <div
                        className="bg-green-500 h-2 rounded-full transition-all duration-300"
                        style={{ width: `${consistencyScore * 100}%` }}
                      />
                    </div>
                    <span className="text-white font-semibold w-12">{consistencyScore.toFixed(2)}</span>
                  </div>
                </div>

                <div>
                  <div className="text-sm text-slate-400 mb-1">Vector Memory</div>
                  <div className="text-white font-semibold text-2xl">
                    {vectorMemory.length}
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Main Display */}
          <div className="lg:col-span-2 space-y-6">
            {/* Knowledge Graph */}
            <div className="bg-slate-800 rounded-lg p-6 border border-blue-500/30">
              <h2 className="text-xl font-semibold text-white mb-4 flex items-center gap-2">
                <Network className="w-5 h-5 text-purple-400" />
                GraphRAG Knowledge Network
              </h2>

              <canvas
                ref={canvasRef}
                width={600}
                height={300}
                className="w-full bg-slate-900 rounded"
              />
            </div>

            {/* Execution Logs */}
            <div className="bg-slate-800 rounded-lg p-6 border border-blue-500/30">
              <h2 className="text-xl font-semibold text-white mb-4 flex items-center gap-2">
                <Brain className="w-5 h-5 text-cyan-400" />
                Execution Trace
              </h2>

              <div className="bg-slate-900 rounded p-4 h-96 overflow-y-auto font-mono text-sm">
                {logs.length === 0 ? (
                  <div className="text-slate-500 italic">
                    No execution logs yet. Enter a task and click Execute.
                  </div>
                ) : (
                  logs.map((log, idx) => (
                    <div key={idx} className="mb-2 text-slate-300">
                      <span className="text-slate-500">
                        [{new Date(log.timestamp).toLocaleTimeString()}]
                      </span>{' '}
                      {log.message}
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Memory Store */}
            <div className="bg-slate-800 rounded-lg p-6 border border-blue-500/30">
              <h2 className="text-xl font-semibold text-white mb-4 flex items-center gap-2">
                <Database className="w-5 h-5 text-orange-400" />
                Vector Memory Store
              </h2>

              <div className="space-y-2 max-h-64 overflow-y-auto">
                {vectorMemory.length === 0 ? (
                  <div className="text-slate-500 italic">No memories stored yet.</div>
                ) : (
                  vectorMemory.map((mem, idx) => (
                    <div key={idx} className="bg-slate-900 rounded p-3 border border-slate-700">
                      <div className="text-white font-semibold mb-1">{mem.task}</div>
                      <div className="flex gap-4 text-sm">
                        <span className="text-blue-400">Route: {mem.route}</span>
                        <span className="text-green-400">Score: {mem.consistency.toFixed(3)}</span>
                        <span className="text-slate-400">{new Date(mem.timestamp).toLocaleString()}</span>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default MetaGodelAgent;
