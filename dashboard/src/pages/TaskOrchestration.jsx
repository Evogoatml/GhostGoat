import React, { useState } from 'react';
import { ListTodo, Play, Clock, CheckCircle, XCircle, Pause, Send } from 'lucide-react';
import Card, { CardHeader } from '../components/Card';
import StatusBadge from '../components/StatusBadge';
import KPICard from '../components/KPICard';
import { useGhostGoat } from '../HybridContext';

export default function TaskOrchestration() {
  const { tasks, stats, submitTask, backendOnline } = useGhostGoat();
  const [newTask, setNewTask] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async () => {
    if (!newTask.trim()) return;
    setSubmitting(true);
    await submitTask(newTask.trim());
    setNewTask('');
    setSubmitting(false);
  };

  const priorityColor = (p) => {
    if (p >= 9) return 'text-red-400';
    if (p >= 7) return 'text-amber-400';
    if (p >= 4) return 'text-blue-400';
    return 'text-slate-400';
  };

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Task Orchestration</h1>
        <p className="text-sm text-slate-400 mt-1">Manage task queue, workflows, and agent assignments</p>
      </div>

      {/* Submit new task */}
      {backendOnline && (
        <Card>
          <div className="p-4 flex gap-3">
            <input
              type="text"
              value={newTask}
              onChange={e => setNewTask(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSubmit()}
              placeholder="Submit a task to the real orchestrator..."
              disabled={submitting}
              className="flex-1 bg-[#0f1117] border border-[#252836] rounded-lg px-4 py-2.5 text-sm text-white placeholder-slate-500 focus:border-indigo-500 focus:outline-none"
            />
            <button
              onClick={handleSubmit}
              disabled={submitting || !newTask.trim()}
              className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-700 rounded-lg text-sm font-medium flex items-center gap-2 transition-colors"
            >
              <Send className="w-4 h-4" />
              {submitting ? 'Running...' : 'Execute'}
            </button>
          </div>
        </Card>
      )}

      {/* KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <KPICard icon={ListTodo} label="Total Tasks" value={stats.totalTasks} color="indigo" />
        <KPICard icon={Play} label="Running" value={stats.runningTasks} color="amber" />
        <KPICard icon={CheckCircle} label="Completed" value={stats.completedTasks} color="emerald" />
        <KPICard icon={XCircle} label="Failed" value={stats.failedTasks} color="red" />
      </div>

      {/* Task Table */}
      <Card>
        <CardHeader icon={ListTodo} title="Task Queue" iconColor="text-amber-400">
          <button className="px-3 py-1.5 text-xs font-medium bg-indigo-600 hover:bg-indigo-700 rounded-lg transition-colors">
            + New Task
          </button>
        </CardHeader>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-[10px] text-slate-500 uppercase tracking-wider border-b border-[#252836]">
                <th className="text-left px-5 py-3">Task</th>
                <th className="text-left px-5 py-3">Status</th>
                <th className="text-left px-5 py-3">Agent</th>
                <th className="text-center px-5 py-3">Priority</th>
                <th className="text-left px-5 py-3">Progress</th>
                <th className="text-left px-5 py-3">Created</th>
                <th className="text-right px-5 py-3">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#252836]">
              {tasks.map(task => (
                <tr key={task.id} className="hover:bg-white/[0.02] transition-colors">
                  <td className="px-5 py-3">
                    <div className="font-medium text-white">{task.description}</div>
                    <div className="text-[10px] text-slate-500">{task.id}</div>
                  </td>
                  <td className="px-5 py-3"><StatusBadge status={task.status} /></td>
                  <td className="px-5 py-3 text-xs text-slate-400">{task.agent || <span className="italic text-slate-600">unassigned</span>}</td>
                  <td className="px-5 py-3 text-center">
                    <span className={`font-bold ${priorityColor(task.priority)}`}>{task.priority}</span>
                  </td>
                  <td className="px-5 py-3 w-40">
                    <div className="flex items-center gap-2">
                      <div className="flex-1 h-1.5 bg-[#252836] rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all duration-700 ${
                            task.status === 'completed' ? 'bg-emerald-500' :
                            task.status === 'failed' ? 'bg-red-500' :
                            task.status === 'running' ? 'bg-amber-500' : 'bg-slate-600'
                          }`}
                          style={{ width: `${task.progress}%` }}
                        />
                      </div>
                      <span className="text-[10px] text-slate-500 w-8">{task.progress}%</span>
                    </div>
                  </td>
                  <td className="px-5 py-3 text-xs text-slate-500">{task.created}</td>
                  <td className="px-5 py-3 text-right">
                    <div className="flex items-center justify-end gap-1">
                      {task.status === 'running' && (
                        <button className="p-1 hover:bg-white/10 rounded" title="Pause">
                          <Pause className="w-3.5 h-3.5 text-slate-400" />
                        </button>
                      )}
                      {task.status === 'queued' && (
                        <button className="p-1 hover:bg-white/10 rounded" title="Start">
                          <Play className="w-3.5 h-3.5 text-emerald-400" />
                        </button>
                      )}
                      {task.status === 'failed' && (
                        <button className="p-1 hover:bg-white/10 rounded" title="Retry">
                          <Play className="w-3.5 h-3.5 text-amber-400" />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Workflow visualization */}
      <Card>
        <CardHeader icon={Clock} title="Active Workflow" iconColor="text-purple-400" />
        <div className="p-6">
          <div className="flex items-center gap-2 overflow-x-auto pb-2">
            {['Decompose Task', 'Select Agents', 'Assign & Execute', 'Collect Results', 'Reflect & Store'].map((step, i) => (
              <React.Fragment key={step}>
                <div className={`flex-shrink-0 px-4 py-3 rounded-lg border text-xs font-medium ${
                  i < 3 ? 'bg-indigo-600/20 border-indigo-500/30 text-indigo-300' :
                  i === 3 ? 'bg-amber-600/20 border-amber-500/30 text-amber-300 animate-pulse' :
                  'bg-[#252836] border-[#353849] text-slate-500'
                }`}>
                  {step}
                </div>
                {i < 4 && (
                  <div className={`flex-shrink-0 w-8 h-0.5 ${i < 3 ? 'bg-indigo-500/50' : 'bg-[#353849]'}`} />
                )}
              </React.Fragment>
            ))}
          </div>
        </div>
      </Card>
    </div>
  );
}
