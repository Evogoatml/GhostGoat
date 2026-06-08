import React from 'react';
import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom';
import {
  LayoutDashboard, Bot, ListTodo, Activity, Network,
  Database, Shield, MessageSquare, Ghost, Wifi, WifiOff,
} from 'lucide-react';

import { HybridProvider, useGhostGoat } from './HybridContext';
import Overview from './pages/Overview';
import AgentRegistry from './pages/AgentRegistry';
import TaskOrchestration from './pages/TaskOrchestration';
import SystemMonitor from './pages/SystemMonitor';
import KnowledgeGraph from './pages/KnowledgeGraph';
import MemoryBrowser from './pages/MemoryBrowser';
import Governance from './pages/Governance';
import CommunicationHub from './pages/CommunicationHub';

const navItems = [
  { to: '/', icon: LayoutDashboard, label: 'Overview' },
  { to: '/agents', icon: Bot, label: 'Agents' },
  { to: '/tasks', icon: ListTodo, label: 'Tasks' },
  { to: '/monitor', icon: Activity, label: 'Monitor' },
  { to: '/knowledge', icon: Network, label: 'Knowledge' },
  { to: '/memory', icon: Database, label: 'Memory' },
  { to: '/governance', icon: Shield, label: 'Governance' },
  { to: '/comms', icon: MessageSquare, label: 'Comms' },
];

function Shell() {
  const { backendOnline, health } = useGhostGoat();

  return (
    <div className="flex h-screen bg-[#0f1117] text-white overflow-hidden">
      {/* Sidebar */}
      <aside className="w-20 lg:w-56 flex-shrink-0 bg-[#161822] border-r border-[#252836] flex flex-col">
        {/* Logo */}
        <div className="h-16 flex items-center gap-3 px-4 border-b border-[#252836]">
          <Ghost className="w-8 h-8 text-indigo-400 flex-shrink-0" />
          <span className="hidden lg:block text-lg font-bold bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-transparent">
            GhostGoat
          </span>
        </div>

        {/* Nav */}
        <nav className="flex-1 py-4 space-y-1 px-2">
          {navItems.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all
                ${isActive
                  ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/30'
                  : 'text-slate-400 hover:text-white hover:bg-white/5 border border-transparent'
                }`
              }
            >
              <Icon className="w-5 h-5 flex-shrink-0" />
              <span className="hidden lg:block">{label}</span>
            </NavLink>
          ))}
        </nav>

        {/* Connection status */}
        <div className="p-4 border-t border-[#252836] space-y-2">
          <div className="hidden lg:flex items-center gap-2 text-xs">
            {backendOnline ? (
              <>
                <Wifi className="w-3.5 h-3.5 text-emerald-400" />
                <span className="text-emerald-400">Backend Live</span>
              </>
            ) : (
              <>
                <WifiOff className="w-3.5 h-3.5 text-amber-400" />
                <span className="text-amber-400">Simulated</span>
              </>
            )}
          </div>
          {/* Small dot for collapsed sidebar */}
          <div className="lg:hidden flex justify-center">
            <span className={`w-2.5 h-2.5 rounded-full ${backendOnline ? 'bg-emerald-400' : 'bg-amber-400'} ${backendOnline ? 'animate-pulse' : ''}`} />
          </div>
          {backendOnline && health && (
            <div className="hidden lg:block text-[10px] text-slate-500">
              Up {Math.round(health.uptime)}s &middot; {Object.values(health.modules).filter(Boolean).length} modules
            </div>
          )}
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-y-auto">
        {/* Connection banner when simulated */}
        {!backendOnline && (
          <div className="bg-amber-600/10 border-b border-amber-500/20 px-6 py-2 text-xs text-amber-300 flex items-center gap-2">
            <WifiOff className="w-3.5 h-3.5" />
            Backend offline — showing simulated data. Start with: <code className="bg-black/30 px-1.5 py-0.5 rounded font-mono">python -m api.server</code>
          </div>
        )}
        <Routes>
          <Route path="/" element={<Overview />} />
          <Route path="/agents" element={<AgentRegistry />} />
          <Route path="/tasks" element={<TaskOrchestration />} />
          <Route path="/monitor" element={<SystemMonitor />} />
          <Route path="/knowledge" element={<KnowledgeGraph />} />
          <Route path="/memory" element={<MemoryBrowser />} />
          <Route path="/governance" element={<Governance />} />
          <Route path="/comms" element={<CommunicationHub />} />
        </Routes>
      </main>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <HybridProvider>
        <Shell />
      </HybridProvider>
    </BrowserRouter>
  );
}
