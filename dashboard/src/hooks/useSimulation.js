import { useState, useEffect, useCallback } from 'react';
import { agents as initialAgents, generateTasks, generateMetrics, generateMessages } from '../data/agentData';

export function useSimulation() {
  const [agents, setAgents] = useState(initialAgents);
  const [tasks, setTasks] = useState(generateTasks);
  const [metrics, setMetrics] = useState(generateMetrics);
  const [messages, setMessages] = useState(generateMessages);
  const [tick, setTick] = useState(0);

  // Simulate live updates every 3 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      setTick(t => t + 1);

      // Jitter agent stats
      setAgents(prev => prev.map(a => {
        if (a.status === 'offline') return a;
        return {
          ...a,
          cpu: Math.max(0, Math.min(100, a.cpu + Math.round((Math.random() - 0.5) * 8))),
          memory: Math.max(0, a.memory + Math.round((Math.random() - 0.5) * 30)),
          health: Math.max(0, Math.min(100, a.health + Math.round((Math.random() - 0.5) * 3))),
        };
      }));

      // Advance task progress
      setTasks(prev => prev.map(t => {
        if (t.status === 'running') {
          const newProgress = Math.min(100, t.progress + Math.round(Math.random() * 8));
          return {
            ...t,
            progress: newProgress,
            status: newProgress >= 100 ? 'completed' : 'running',
          };
        }
        if (t.status === 'queued' && Math.random() > 0.7) {
          return { ...t, status: 'running', agent: 'Brain Core', progress: Math.round(Math.random() * 15) };
        }
        return t;
      }));

      // Append metric point
      setMetrics(prev => {
        const last = prev[prev.length - 1];
        const next = {
          time: new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
          cpu: Math.max(0, Math.min(100, (last?.cpu || 30) + Math.round((Math.random() - 0.5) * 10))),
          memory: Math.max(0, Math.min(100, (last?.memory || 45) + Math.round((Math.random() - 0.5) * 5))),
          tasks: Math.max(0, (last?.tasks || 8) + Math.round((Math.random() - 0.5) * 3)),
          latency: Math.max(5, (last?.latency || 50) + Math.round((Math.random() - 0.5) * 15)),
        };
        return [...prev.slice(-59), next];
      });
    }, 3000);
    return () => clearInterval(interval);
  }, []);

  const activeAgents = agents.filter(a => a.status === 'active').length;
  const totalTasks = tasks.length;
  const runningTasks = tasks.filter(t => t.status === 'running').length;
  const completedTasks = tasks.filter(t => t.status === 'completed').length;
  const failedTasks = tasks.filter(t => t.status === 'failed').length;
  const avgHealth = Math.round(agents.reduce((s, a) => s + a.health, 0) / agents.length);
  const totalCpu = agents.reduce((s, a) => s + a.cpu, 0);

  return {
    agents, tasks, metrics, messages, tick,
    stats: { activeAgents, totalTasks, runningTasks, completedTasks, failedTasks, avgHealth, totalCpu },
  };
}
