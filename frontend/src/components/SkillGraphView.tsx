import { useEffect, useMemo, useState } from "react";
import type { Json } from "../types/api";

export type GraphState = "acquired" | "in_progress" | "missing";
const COLOR: Record<GraphState, string> = { acquired: "var(--graph-acquired)", in_progress: "var(--graph-progress)", missing: "var(--graph-missing)" };
const WORD: Record<GraphState, string> = { acquired: "acquired", in_progress: "in progress", missing: "missing" };

interface Props {
  network: { nodes: Json[]; edges: Json[] };
  role: string;
  onSelect: (slug: string) => void;
  selected?: string | null;
  filter?: GraphState | "all";
  group?: string;
  animate?: boolean;   // draw connections in (use once, when the page appears)
}

/**
 * One renderer for the dashboard preview and the full Skill Graph page. States are drawn differently, not just recoloured:
 * acquired = solid, in progress = amber with an arc showing the score, missing = faint fill with a solid outline.
 * Selecting a skill highlights its connections and fades the rest. Everything is computed from the data passed in.
 */
export default function SkillGraphView({ network, role, onSelect, selected = null, filter = "all", group = "all", animate = false }: Props) {
  const { pos, W, H } = useMemo(() => {
    const cols: Record<number, Json[]> = {};
    network.nodes.forEach((n) => (cols[n.depth] ??= []).push(n));
    const depths = Object.keys(cols).map(Number).sort((a, b) => a - b);
    depths.forEach((d) => cols[d].sort((a, b) => (a.group < b.group ? -1 : a.group > b.group ? 1 : a.name < b.name ? -1 : 1)));
    const maxN = Math.max(...depths.map((d) => cols[d].length));
    const p: Record<string, { x: number; y: number }> = {};
    depths.forEach((d, ci) => {
      let arr = cols[d];
      if (ci > 0) {   // order each column by the average height of its prerequisites, so connections cross as little as possible
        const key = (n: Json) => {
          const ys = network.edges.filter((e) => e.target === n.id && p[e.source]).map((e) => p[e.source].y);
          return ys.length ? ys.reduce((a: number, b: number) => a + b, 0) / ys.length : 1e9;
        };
        arr = [...arr].sort((a, b) => key(a) - key(b) || (a.name < b.name ? -1 : 1));
      }
      arr.forEach((n, i) => { p[n.id] = { x: 64 + ci * 150, y: 34 + (maxN - arr.length) * 26 + i * 52 }; });
    });
    return { pos: p, W: 128 + 150 * (depths.length - 1), H: 70 + 52 * (maxN - 1) };
  }, [network]);

  // The draw-in plays once when the graph first appears; it must not replay when a skill is deselected.
  const [drawing, setDrawing] = useState(animate);
  useEffect(() => {
    if (!animate) return;
    const t = window.setTimeout(() => setDrawing(false), 1300);
    return () => window.clearTimeout(t);
  }, [animate]);

  const sel = selected && network.nodes.some((n) => n.id === selected) ? selected : null;
  const near = new Set<string>();
  if (sel) { near.add(sel); network.edges.forEach((e) => { if (e.source === sel) near.add(e.target); if (e.target === sel) near.add(e.source); }); }
  const matches = (n: Json) => (filter === "all" || n.state === filter) && (group === "all" || n.group === group);
  const nextUp = new Set(network.nodes.filter((n) => n.current).map((n) => n.id));

  return (
    <div className="overflow-x-auto rounded-xl border border-mist bg-inset/70">
      <svg viewBox={`0 0 ${W} ${H}`} role="group" aria-label={`Skill network for ${role}`} className={`graph block h-auto w-full min-w-[640px] ${drawing ? "graph-draw" : ""}`}>
        {network.edges.map((e) => {
          const a = pos[e.source], b = pos[e.target], x1 = a.x + 16, x2 = b.x - 16, xm = (x1 + x2) / 2;
          const touches = sel && (e.source === sel || e.target === sel);
          const cls = `edge ${touches ? "edge-hot" : sel ? "edge-dim" : ""}`;
          const toward = !sel && nextUp.has(e.target);
          return <path key={`${e.source}-${e.target}`} className={cls} pathLength={1} fill="none" stroke={toward ? "rgb(var(--teal))" : "var(--graph-edge)"} strokeWidth={toward ? 2 : 1.4} d={`M${x1} ${a.y} C${xm} ${a.y} ${xm} ${b.y} ${x2} ${b.y}`} />;
        })}
        {network.nodes.map((n) => {
          const p = pos[n.id], state = n.state as GraphState, c = COLOR[state], sc = Math.max(0, Math.min(100, Math.round(n.score)));
          const cls = `node ${sel === n.id ? "node-sel" : ""} ${sel && !near.has(n.id) ? "node-dim" : ""} ${!matches(n) ? "node-dim2" : ""} cursor-pointer`;
          const fire = () => onSelect(n.id);
          return (
            <g key={n.id} className={cls} tabIndex={0} role="link" aria-label={`${n.name}: ${sc}%, ${WORD[state]}${n.current ? ", next up" : ""}${n.is_bottleneck ? ", bottleneck skill" : ""}${n.review_status === "overdue" || n.review_status === "due" ? ", review due" : ""}`}
              onClick={fire} onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); fire(); } }}>
              {n.current && <circle cx={p.x} cy={p.y} r="24" fill="none" stroke="rgb(var(--teal))" strokeWidth="2.5" className="animate-pulse" />}
              {state === "in_progress" && sc > 0 && (
                <circle cx={p.x} cy={p.y} r="19.5" fill="none" stroke={c} strokeWidth="2.4" strokeLinecap="round" pathLength={100} strokeDasharray={`${sc} ${100 - sc}`} transform={`rotate(-90 ${p.x} ${p.y})`} opacity={0.9} />
              )}
              <circle className="core" cx={p.x} cy={p.y} r={sel === n.id ? 17 : 15} fill={c} fillOpacity={state === "acquired" ? 0.95 : state === "in_progress" ? 0.85 : 0.12}
                stroke={state === "missing" ? c : n.supporting ? "rgb(var(--text))" : c} strokeWidth={state === "missing" ? 2.2 : n.supporting ? 1.6 : 0}
                strokeDasharray={n.supporting && state !== "missing" ? "3 2" : undefined} style={{ filter: `drop-shadow(0 0 ${state === "acquired" ? 6 : 4}px ${c})` }} />
              {n.is_bottleneck && <polygon points={`${p.x},${p.y - 27} ${p.x + 7},${p.y - 20} ${p.x},${p.y - 13} ${p.x - 7},${p.y - 20}`} fill="var(--graph-progress)" stroke="rgb(var(--text))" strokeWidth="1" />}
              {(n.review_status === "overdue" || n.review_status === "due") && <circle cx={p.x + 14} cy={p.y - 13} r="4.5" fill="rgb(var(--teal))" stroke="rgb(var(--inset))" strokeWidth="1.4" />}
              <text x={p.x} y={p.y + 4} textAnchor="middle" fontSize="9" fontWeight="700" fill={state === "missing" ? c : "var(--graph-number)"}>{sc}</text>
              <text x={p.x} y={p.y + 32} textAnchor="middle" fontSize="11" fill="var(--graph-label)">{n.name.length > 15 ? `${n.name.slice(0, 14)}…` : n.name}</text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

export function GraphLegend() {
  return (
    <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-ink-soft">
      <span><i className="mr-1.5 inline-block h-2.5 w-2.5 rounded-full bg-moss align-middle" />Acquired</span>
      <span><i className="mr-1.5 inline-block h-2.5 w-2.5 rounded-full bg-signal align-middle" />In progress (arc = score)</span>
      <span><i className="mr-1.5 inline-block h-2.5 w-2.5 rounded-full border-2 border-alert align-middle" />Missing</span>
      <span><i className="mr-1.5 inline-block h-2.5 w-2.5 rounded-full border-2 border-glow-cyan align-middle" />Next up</span>
      <span><i className="mr-1.5 inline-block h-2.5 w-2.5 rounded-full border border-dashed border-white align-middle" />Prerequisite</span>
      <span><span aria-hidden className="mr-1.5 text-signal">◆</span>Bottleneck</span>
      <span><i className="mr-1.5 inline-block h-2.5 w-2.5 rounded-full bg-glow-cyan align-middle" />Review due</span>
    </div>
  );
}
