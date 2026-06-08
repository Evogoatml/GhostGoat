import React, { useState } from 'react';
import { Database, Search, Filter, ExternalLink } from 'lucide-react';
import Card, { CardHeader } from '../components/Card';
import StatusBadge from '../components/StatusBadge';
import { vectorMemoryEntries } from '../data/agentData';

export default function MemoryBrowser() {
  const [search, setSearch] = useState('');
  const [filterDomain, setFilterDomain] = useState('all');

  const domains = [...new Set(vectorMemoryEntries.map(v => v.metadata.domain))];
  const filtered = vectorMemoryEntries
    .filter(v => v.content.toLowerCase().includes(search.toLowerCase()))
    .filter(v => filterDomain === 'all' || v.metadata.domain === filterDomain);

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Memory Browser</h1>
        <p className="text-sm text-slate-400 mt-1">Search and browse the vector memory store ({vectorMemoryEntries.length} entries)</p>
      </div>

      {/* Search */}
      <div className="flex flex-wrap gap-3">
        <div className="relative flex-1 min-w-[250px]">
          <Search className="absolute left-3 top-2.5 w-4 h-4 text-slate-500" />
          <input
            type="text" placeholder="Semantic search across vector memory..."
            value={search} onChange={e => setSearch(e.target.value)}
            className="w-full bg-[#1a1d2e] border border-[#252836] rounded-lg pl-10 pr-4 py-2 text-sm text-white placeholder-slate-500 focus:border-indigo-500 focus:outline-none"
          />
        </div>
        <select value={filterDomain} onChange={e => setFilterDomain(e.target.value)}
          className="bg-[#1a1d2e] border border-[#252836] rounded-lg px-3 py-2 text-sm text-white focus:border-indigo-500 focus:outline-none">
          <option value="all">All Domains</option>
          {domains.map(d => <option key={d} value={d}>{d}</option>)}
        </select>
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
                <div className="flex-shrink-0 text-right">
                  <div className="text-lg font-bold text-indigo-400">{entry.similarity.toFixed(2)}</div>
                  <div className="text-[10px] text-slate-500">similarity</div>
                </div>
              </div>

              {/* Similarity bar */}
              <div className="h-1 bg-[#252836] rounded-full overflow-hidden mb-3">
                <div
                  className="h-full bg-gradient-to-r from-indigo-500 to-purple-500 rounded-full"
                  style={{ width: `${entry.similarity * 100}%` }}
                />
              </div>

              {/* Metadata */}
              <div className="flex flex-wrap items-center gap-3 text-[10px]">
                <span className="px-2 py-0.5 bg-indigo-500/10 text-indigo-300 rounded border border-indigo-500/20">
                  {entry.metadata.domain}
                </span>
                <span className="text-slate-500">Source: <span className="text-slate-400">{entry.metadata.source}</span></span>
                <span className="text-slate-500">Dim: <span className="text-slate-400">{entry.embedding_dim}</span></span>
                <span className="text-slate-500">{entry.timestamp}</span>
                <span className="text-slate-600 font-mono">{entry.id}</span>
              </div>
            </div>
          </Card>
        ))}
      </div>

      {filtered.length === 0 && (
        <div className="text-center py-16 text-slate-500">
          <Database className="w-10 h-10 mx-auto mb-3 opacity-30" />
          <p>No memory entries match your search</p>
        </div>
      )}

      {/* Stats */}
      <Card>
        <CardHeader icon={Database} title="Store Statistics" iconColor="text-orange-400" />
        <div className="p-5 grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            ['Total Entries', vectorMemoryEntries.length],
            ['Embedding Dim', '768'],
            ['Index Type', 'HNSW'],
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
