import { useMemo, useRef, useState } from "react";
import type { Json } from "../types/api";

/** Dependency graph: pan (drag), zoom (wheel/buttons), click a node. Edges run prerequisite -> dependent. */
export default function SkillGraph({ graph, onSelect }: { graph: Json; onSelect?: (slug: string) => void }) {
  const [view, setView] = useState({ x: 0, y: 0, k: 1 });
  const drag = useRef<{ x: number; y: number } | null>(null);

  const layout = useMemo(() => {
    const nodes: Json[] = graph.nodes;
    const incoming: Record<string, string[]> = {};
    graph.edges.forEach((e: Json) => (incoming[e.target] ??= []).push(e.source));
    const depth: Record<string, number> = {};
    const d = (id: string, seen: string[] = []): number => {
      if (depth[id] !== undefined) return depth[id];
      if (seen.includes(id)) return 0;
      return (depth[id] = Math.max(-1, ...(incoming[id] ?? []).map((p) => d(p, [...seen, id]))) + 1);
    };
    nodes.forEach((n) => d(n.id));
    const cols: Record<number, Json[]> = {};
    nodes.forEach((n) => (cols[depth[n.id]] ??= []).push(n));
    const pos: Record<string, { x: number; y: number }> = {};
    Object.entries(cols).forEach(([c, ns]) => ns.forEach((n, i) => (pos[n.id] = { x: 90 + Number(c) * 190, y: 60 + i * 70 + (4 - ns.length) * 0 })));
    return pos;
  }, [graph]);

  const w = Math.max(...Object.values(layout).map((p) => p.x)) + 110;
  const h = Math.max(...Object.values(layout).map((p) => p.y)) + 70;
  const zoom = (f: number) => setView((v) => ({ ...v, k: Math.max(0.4, Math.min(2.5, v.k * f)) }));

  return (
    <div>
      <div className="mb-2 flex gap-2">
        <button type="button" className="btn-quiet px-3 py-1" onClick={() => zoom(1.2)} aria-label="Zoom in">+</button>
        <button type="button" className="btn-quiet px-3 py-1" onClick={() => zoom(1 / 1.2)} aria-label="Zoom out">−</button>
        <button type="button" className="btn-quiet px-3 py-1" onClick={() => setView({ x: 0, y: 0, k: 1 })}>Reset</button>
        <span className="self-center text-xs text-ink-faint">Drag to pan. Click a skill to open it.</span>
      </div>
      <svg
        role="group" aria-label="Skill dependency graph" viewBox={`0 0 ${w} ${h}`} className="h-72 w-full cursor-grab touch-none rounded-lg border border-mist bg-[#060B1E]/60"
        onWheel={(e) => { e.preventDefault(); zoom(e.deltaY < 0 ? 1.1 : 1 / 1.1); }}
        onPointerDown={(e) => { drag.current = { x: e.clientX, y: e.clientY }; (e.target as Element).setPointerCapture?.(e.pointerId); }}
        onPointerMove={(e) => { if (!drag.current) return; const dx = e.clientX - drag.current.x, dy = e.clientY - drag.current.y; drag.current = { x: e.clientX, y: e.clientY }; setView((v) => ({ ...v, x: v.x + dx, y: v.y + dy })); }}
        onPointerUp={() => (drag.current = null)}
      >
        <defs><marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#8FB0FF" /></marker></defs>
        <g transform={`translate(${view.x} ${view.y}) scale(${view.k})`}>
          {graph.edges.map((e: Json) => {
            const a = layout[e.source], b = layout[e.target];
            return a && b ? <line key={`${e.source}-${e.target}`} x1={a.x + 60} y1={a.y} x2={b.x - 60} y2={b.y} stroke="rgba(143,176,255,.5)" strokeWidth="1.5" markerEnd="url(#arr)" /> : null;
          })}
          {graph.nodes.map((n: Json) => {
            const p = layout[n.id];
            const focus = n.role === "focus";
            return (
              <g key={n.id} transform={`translate(${p.x - 60} ${p.y - 18})`} className="cursor-pointer" tabIndex={0} role="button" aria-label={`${n.name} (${n.role})`}
                 onClick={() => onSelect?.(n.id)} onKeyDown={(e) => e.key === "Enter" && onSelect?.(n.id)}>
                <rect width="120" height="36" rx="8" fill={focus ? "#5B6CFF" : "#0E1636"} stroke={focus ? "#B3C8FF" : "#5A6AA8"} />
                <text x="60" y="23" textAnchor="middle" fontSize="13" fill="#EAEFFF">{n.name.length > 16 ? n.name.slice(0, 15) + "…" : n.name}</text>
              </g>
            );
          })}
        </g>
      </svg>
      <p className="mt-1 text-xs text-ink-faint">Arrows point from a prerequisite to the skill that depends on it.</p>
    </div>
  );
}
