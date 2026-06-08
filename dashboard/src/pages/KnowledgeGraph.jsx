import React, { useRef, useEffect, useState, useCallback } from 'react';
import { Network, ZoomIn, ZoomOut, Maximize } from 'lucide-react';
import Card, { CardHeader } from '../components/Card';
import { knowledgeNodes, knowledgeEdges } from '../data/agentData';

const groupColors = {
  reasoning: { fill: '#6366f1', stroke: '#818cf8', bg: 'rgba(99,102,241,0.15)' },
  memory: { fill: '#10b981', stroke: '#34d399', bg: 'rgba(16,185,129,0.15)' },
  knowledge: { fill: '#f59e0b', stroke: '#fbbf24', bg: 'rgba(245,158,11,0.15)' },
  expert: { fill: '#8b5cf6', stroke: '#a78bfa', bg: 'rgba(139,92,246,0.15)' },
  orchestrator: { fill: '#3b82f6', stroke: '#60a5fa', bg: 'rgba(59,130,246,0.15)' },
  network: { fill: '#06b6d4', stroke: '#22d3ee', bg: 'rgba(6,182,212,0.15)' },
  governance: { fill: '#ef4444', stroke: '#f87171', bg: 'rgba(239,68,68,0.15)' },
  asi: { fill: '#ec4899', stroke: '#f472b6', bg: 'rgba(236,72,153,0.15)' },
};

export default function KnowledgeGraph() {
  const canvasRef = useRef(null);
  const [zoom, setZoom] = useState(1);
  const [offset, setOffset] = useState({ x: 0, y: 0 });
  const [dragging, setDragging] = useState(null);
  const [hoveredNode, setHoveredNode] = useState(null);
  const [nodes, setNodes] = useState(knowledgeNodes);
  const animFrame = useRef(null);

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const w = canvas.width;
    const h = canvas.height;

    ctx.clearRect(0, 0, w, h);
    ctx.save();
    ctx.translate(offset.x, offset.y);
    ctx.scale(zoom, zoom);

    // Draw edges
    knowledgeEdges.forEach(edge => {
      const from = nodes.find(n => n.id === edge.from);
      const to = nodes.find(n => n.id === edge.to);
      if (!from || !to) return;

      ctx.beginPath();
      ctx.moveTo(from.x, from.y);
      ctx.lineTo(to.x, to.y);
      ctx.strokeStyle = 'rgba(100, 116, 139, 0.25)';
      ctx.lineWidth = 1.5;
      ctx.stroke();

      // Animated particle
      const t = (Date.now() % 3000) / 3000;
      const px = from.x + (to.x - from.x) * t;
      const py = from.y + (to.y - from.y) * t;
      ctx.beginPath();
      ctx.arc(px, py, 2, 0, Math.PI * 2);
      ctx.fillStyle = 'rgba(99, 102, 241, 0.6)';
      ctx.fill();
    });

    // Draw nodes
    nodes.forEach(node => {
      const colors = groupColors[node.group] || groupColors.reasoning;
      const isHovered = hoveredNode === node.id;
      const radius = isHovered ? 24 : 18;

      // Glow
      ctx.beginPath();
      ctx.arc(node.x, node.y, radius + 8, 0, Math.PI * 2);
      ctx.fillStyle = colors.bg;
      ctx.fill();

      // Node circle
      ctx.beginPath();
      ctx.arc(node.x, node.y, radius, 0, Math.PI * 2);
      ctx.fillStyle = colors.fill;
      ctx.fill();
      ctx.strokeStyle = colors.stroke;
      ctx.lineWidth = isHovered ? 3 : 2;
      ctx.stroke();

      // Label
      ctx.fillStyle = '#e2e8f0';
      ctx.font = `${isHovered ? 'bold ' : ''}11px Inter, system-ui, sans-serif`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'top';
      ctx.fillText(node.label, node.x, node.y + radius + 6);
    });

    ctx.restore();
    animFrame.current = requestAnimationFrame(draw);
  }, [nodes, zoom, offset, hoveredNode]);

  useEffect(() => {
    animFrame.current = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(animFrame.current);
  }, [draw]);

  // Mouse handlers
  const getCanvasPos = (e) => {
    const rect = canvasRef.current.getBoundingClientRect();
    return {
      x: (e.clientX - rect.left - offset.x) / zoom,
      y: (e.clientY - rect.top - offset.y) / zoom,
    };
  };

  const handleMouseDown = (e) => {
    const pos = getCanvasPos(e);
    const hit = nodes.find(n => Math.hypot(n.x - pos.x, n.y - pos.y) < 20);
    if (hit) setDragging(hit.id);
  };

  const handleMouseMove = (e) => {
    const pos = getCanvasPos(e);
    if (dragging) {
      setNodes(prev => prev.map(n => n.id === dragging ? { ...n, x: pos.x, y: pos.y } : n));
    } else {
      const hit = nodes.find(n => Math.hypot(n.x - pos.x, n.y - pos.y) < 20);
      setHoveredNode(hit?.id || null);
    }
  };

  const handleMouseUp = () => setDragging(null);

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Knowledge Graph</h1>
        <p className="text-sm text-slate-400 mt-1">Interactive visualization of GhostGoat's component relationships</p>
      </div>

      <Card>
        <CardHeader icon={Network} title="System Architecture Graph" iconColor="text-purple-400">
          <div className="flex items-center gap-2">
            <button onClick={() => setZoom(z => Math.min(z + 0.2, 3))} className="p-1.5 bg-[#252836] hover:bg-[#2f3347] rounded-lg">
              <ZoomIn className="w-4 h-4" />
            </button>
            <button onClick={() => setZoom(z => Math.max(z - 0.2, 0.3))} className="p-1.5 bg-[#252836] hover:bg-[#2f3347] rounded-lg">
              <ZoomOut className="w-4 h-4" />
            </button>
            <button onClick={() => { setZoom(1); setOffset({ x: 0, y: 0 }); }} className="p-1.5 bg-[#252836] hover:bg-[#2f3347] rounded-lg">
              <Maximize className="w-4 h-4" />
            </button>
          </div>
        </CardHeader>
        <div className="p-2">
          <canvas
            ref={canvasRef}
            width={900}
            height={500}
            className="w-full bg-[#0f1117] rounded-lg cursor-grab active:cursor-grabbing"
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onMouseLeave={handleMouseUp}
          />
        </div>
      </Card>

      {/* Legend */}
      <div className="flex flex-wrap gap-3">
        {Object.entries(groupColors).map(([group, colors]) => (
          <div key={group} className="flex items-center gap-2 px-3 py-1.5 bg-[#1a1d2e] rounded-lg border border-[#252836]">
            <div className="w-3 h-3 rounded-full" style={{ backgroundColor: colors.fill }} />
            <span className="text-xs text-slate-400 capitalize">{group}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
