/**
 * Hybrid API hook.
 * Tries the real GhostGoat backend (port 8420).
 * Falls back to simulated data if backend is offline.
 */
import { useState, useEffect, useCallback, useRef } from 'react';

const API_BASE = 'http://localhost:8420/api';
const POLL_INTERVAL = 3000;

// ── Fetch with timeout ──────────────────────────────────────────────
async function apiFetch(path, options = {}) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 2000);
  try {
    const res = await fetch(`${API_BASE}${path}`, {
      ...options,
      signal: controller.signal,
      headers: { 'Content-Type': 'application/json', ...options.headers },
    });
    clearTimeout(timeout);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (e) {
    clearTimeout(timeout);
    throw e;
  }
}

// ── Main hybrid hook ────────────────────────────────────────────────
export function useHybridData() {
  const [backendOnline, setBackendOnline] = useState(false);
  const [health, setHealth] = useState(null);
  const [agents, setAgents] = useState([]);
  const [tasks, setTasks] = useState([]);
  const [metrics, setMetrics] = useState(null);
  const [messages, setMessages] = useState([]);
  const [policies, setPolicies] = useState({ policies: [], audit_log: [] });
  const [services, setServices] = useState({});
  const [error, setError] = useState(null);
  const tickRef = useRef(0);

  // Check backend health
  const checkHealth = useCallback(async () => {
    try {
      const data = await apiFetch('/health');
      setHealth(data);
      setBackendOnline(true);
      setError(null);
      return true;
    } catch {
      setBackendOnline(false);
      return false;
    }
  }, []);

  // Fetch all real data
  const fetchAll = useCallback(async () => {
    try {
      const [agentRes, taskRes, metricRes, msgRes, polRes, svcRes] = await Promise.allSettled([
        apiFetch('/agents'),
        apiFetch('/tasks'),
        apiFetch('/system/metrics'),
        apiFetch('/messages'),
        apiFetch('/governance/policies'),
        apiFetch('/services'),
      ]);

      if (agentRes.status === 'fulfilled') setAgents(agentRes.value.agents || []);
      if (taskRes.status === 'fulfilled') setTasks(taskRes.value.tasks || []);
      if (metricRes.status === 'fulfilled') setMetrics(metricRes.value);
      if (msgRes.status === 'fulfilled') setMessages(msgRes.value.messages || []);
      if (polRes.status === 'fulfilled') setPolicies(polRes.value);
      if (svcRes.status === 'fulfilled') setServices(svcRes.value.services || {});
    } catch (e) {
      setError(e.message);
    }
  }, []);

  // Poll loop
  useEffect(() => {
    let mounted = true;

    const poll = async () => {
      if (!mounted) return;
      const online = await checkHealth();
      if (online) await fetchAll();
      tickRef.current += 1;
    };

    poll(); // initial
    const interval = setInterval(poll, POLL_INTERVAL);
    return () => { mounted = false; clearInterval(interval); };
  }, [checkHealth, fetchAll]);

  // ── Actions (POST to real backend) ────────────────────────────────
  const submitTask = useCallback(async (description, priority = 5) => {
    if (!backendOnline) return { error: 'Backend offline' };
    try {
      const res = await apiFetch('/tasks', {
        method: 'POST',
        body: JSON.stringify({ description, priority }),
      });
      await fetchAll(); // refresh
      return res;
    } catch (e) {
      return { error: e.message };
    }
  }, [backendOnline, fetchAll]);

  const sendMessage = useCallback(async (from_agent, to_agent, content, type = 'task_assign') => {
    if (!backendOnline) return { error: 'Backend offline' };
    try {
      const res = await apiFetch('/messages', {
        method: 'POST',
        body: JSON.stringify({ from_agent, to_agent, content, type }),
      });
      await fetchAll();
      return res;
    } catch (e) {
      return { error: e.message };
    }
  }, [backendOnline, fetchAll]);

  const searchKnowledge = useCallback(async (query, limit = 10) => {
    if (!backendOnline) return { results: [], error: 'Backend offline' };
    try {
      return await apiFetch(`/knowledge/search?q=${encodeURIComponent(query)}&limit=${limit}`);
    } catch (e) {
      return { results: [], error: e.message };
    }
  }, [backendOnline]);

  return {
    backendOnline,
    health,
    agents,
    tasks,
    metrics,
    messages,
    policies,
    services,
    error,
    tick: tickRef.current,
    // Actions
    submitTask,
    sendMessage,
    searchKnowledge,
  };
}
