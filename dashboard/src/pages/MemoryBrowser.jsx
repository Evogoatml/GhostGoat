import React, { useEffect, useState } from 'react';
import { Database, Search } from 'lucide-react';
import Card, { CardHeader } from '../components/Card';
import { useGhostGoat } from '../HybridContext';

export default function MemoryBrowser() {
  const [search, setSearch] = useState('');
  const [entries, setEntries] = useState([]);
  const { backendOnline, memoryEntries, memoryStats, searchMemory } = useGhostGoat();

  useEffect(() => {
    if (!search.trim()) {
      setEntries(memoryEntries);
      return;
    }
    if (backendOnline) {
      let active = true;
      searchMemory(search).then(result => {
        if (active) setEntries(result.entries || []);
      });
      return () => { active = false; };
    }
    setEntries([]);
  }, [search, backendOnline, memoryEntries, searchMemory]);

  const domains = [...new Set(entries.map(entry => entry.category || 'uncategorized'))];
  const filtered = entries;

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Memory Browser</h1>
        <p className="text-sm text-slate-400 mt-1">
          {backendOnline ? `Knowledge store (${memoryStats?.total_entries ?? 0} entries)` : 'Live memory unavailable'}
        </p>
      </div>

      {/* Search */}
      <div className="flex flex-wrap gap-3">
        <div className="relative flex-1 min-w-[250px]">
          <Search className="absolute left-3 top-2.5 w-4 h-4 text-slate-500" />
          <input
            type="text" placeholder="Search stored task results and knowledge..."
            value={search} onChange={e => setSearch(e.target.value)}
            className="w-full bg-[#1a1d2e] border border-[#252836] rounded-lg pl-10 pr-4 py-2 text-sm text-white placeholder-slate-500 focus:border-indigo-500 focus:outline-none"
          />
        </div>
      </div>

      {/* Memory entries */}
      <div className="space-y-3">
        {filtered.map(entry => (
          <Card key={entry.id}>
            <div className="p-5">
              <div className="flex items-start justify-between gap-4 mb-3">
                <div className="flex-1">
                  <p className="text-sm text-white leading-relaxed">{entry.content}</p>
                </div>
              </div>

              {/* Metadata */}
              <div className="flex flex-wrap items-center gap-3 text-[10px]">
                <span className="px-2 py-0.5 bg-indigo-500/10 text-indigo-300 rounded border border-indigo-500/20">
                  {entry.category || 'uncategorized'}
                </span>
                <span className="text-slate-500">Source: <span className="text-slate-400">{entry.source || 'unknown'}</span></span>
                <span className="text-slate-500">Uses: <span className="text-slate-400">{entry.usage ?? 0}</span></span>
                <span className="text-slate-600 font-mono">{entry.id}</span>
              </div>
            </div>
          </Card>
        ))}
      </div>

      {filtered.length === 0 && (
        <div className="text-center py-16 text-slate-500">
          <Database className="w-10 h-10 mx-auto mb-3 opacity-30" />
          <p>{backendOnline ? 'No stored entries match your search' : 'Connect the API to browse live memory'}</p>
        </div>
      )}

      {/* Stats */}
      <Card>
        <CardHeader icon={Database} title="Store Statistics" iconColor="text-orange-400" />
        <div className="p-5 grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            ['Total Entries', memoryStats?.total_entries ?? '—'],
            ['Algorithms', memoryStats?.total_algorithms ?? '—'],
            ['Storage', memoryStats?.storage_path ? 'SQLite-free JSONL' : '—'],
            ['Domains', domains.length],
          ].map(([k, v]) => (
            <div key={k}>
              <div className="text-[10px] text-slate-500 uppercase tracking-wider">{k}</div>
              <div className="text-lg font-bold text-white mt-1">{v}</div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
