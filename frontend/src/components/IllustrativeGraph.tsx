import { useState } from "react";
const nodes = [
  {id:"html", name:"HTML & CSS", x:86, y:93, tier:0, description:"Start with semantic structure and responsive layouts. These foundations support the interface layer."},
  {id:"js", name:"JavaScript", x:86, y:230, tier:0, description:"Use programming fundamentals and browser behavior before building component-based interfaces."},
  {id:"sql", name:"Databases", x:86, y:367, tier:0, description:"Learn data modeling and queries before connecting persistent data to an application."},
  {id:"react", name:"React", x:270, y:93, tier:1, description:"Build reusable interfaces on top of HTML, CSS and JavaScript foundations."},
  {id:"api", name:"APIs", x:270, y:230, tier:1, description:"Connect application logic and data through validated request and response contracts."},
  {id:"auth", name:"Authentication", x:270, y:367, tier:1, description:"Protect accounts and private data when adding server-side application features."},
  {id:"goal", name:"Full-stack goal", x:458, y:230, tier:2, description:"Bring interface, API, data and account security skills together in a deployed application."},
];
const edges = [["html","react"],["js","react"],["js","api"],["sql","api"],["api","auth"],["react","goal"],["api","goal"],["auth","goal"]];
export default function IllustrativeGraph() {
  const [selected, setSelected] = useState("react");
  const node = nodes.find(n => n.id === selected)!;
  const related = new Set([selected,...edges.filter(e=>e.includes(selected)).flat()]);
  return <div className="hero-graph-card">
    <div className="flex items-center justify-between gap-2 px-5 pt-5"><span className="eyebrow">A connected way to learn</span><span className="sample-badge">Illustrative graph</span></div>
    <div className="graph-stage">
      <svg viewBox="0 0 560 460" role="group" aria-label="Illustrative full-stack skill dependencies. Select a node to read its purpose." className="demo-graph">
        <defs>
          <pattern id="graph-grid" width="28" height="28" patternUnits="userSpaceOnUse"><circle cx="1" cy="1" r="1" fill="var(--graph-edge)" opacity=".3" /></pattern>
          <marker id="demo-arrow" viewBox="0 0 8 8" refX="6" refY="4" markerWidth="5" markerHeight="5" orient="auto"><path d="M0 0 L8 4 L0 8" fill="var(--graph-edge)" /></marker>
        </defs>
        <rect width="560" height="460" fill="url(#graph-grid)" />
        <text x="86" y="33" textAnchor="middle" className="tier-label">FOUNDATIONS</text><text x="270" y="33" textAnchor="middle" className="tier-label">BUILD & CONNECT</text><text x="458" y="33" textAnchor="middle" className="tier-label">YOUR DIRECTION</text>
        {edges.map(([a,b]) => {
          const from=nodes.find(n=>n.id===a)!, to=nodes.find(n=>n.id===b)!;
          const same=from.x===to.x;
          const path=same ? `M${from.x} ${from.y+29} L${to.x} ${to.y-30}` : `M${from.x+36} ${from.y} C${from.x+110} ${from.y} ${to.x-110} ${to.y} ${to.x-38} ${to.y}`;
          return <path key={a+b} d={path} fill="none" stroke={a===selected || b===selected ? "rgb(var(--accent))" : "var(--graph-edge)"} strokeWidth={a===selected || b===selected ? 2.5 : 1.4} opacity={related.has(a)&&related.has(b)?1:.3} markerEnd="url(#demo-arrow)" className="demo-edge" />;
        })}
        {nodes.map((n,i)=><g key={n.id} role="button" tabIndex={0} aria-label={`Select ${n.name}`} aria-pressed={selected===n.id} onClick={()=>setSelected(n.id)} onKeyDown={e=>{if(e.key==="Enter"||e.key===" "){e.preventDefault();setSelected(n.id);}}} className={`demo-node ${selected===n.id?"selected":""}`} style={{animationDelay:`${i*45}ms`}} opacity={related.has(n.id)?1:.6}>
          <circle className="demo-halo" cx={n.x} cy={n.y} r={n.tier===2?39:35} fill="rgb(var(--tint))" />
          <circle className="demo-node-core" cx={n.x} cy={n.y} r={n.tier===2?29:25} fill="rgb(var(--surface))" stroke={selected===n.id?"rgb(var(--accent))":"rgb(var(--border))"} strokeWidth={selected===n.id?2.5:1.5} />
          <text x={n.x} y={n.y+5} textAnchor="middle" fontSize="14" fontWeight="700" fill="rgb(var(--accent))" aria-hidden="true">{n.tier===2?"◎":n.id==="html"?"</>":n.id==="js"?"JS":n.id==="sql"?"DB":n.id==="react"?"⚛":n.id==="api"?"{ }":"✓"}</text>
          <text x={n.x} y={n.y+55} textAnchor="middle" fontSize="12" fontWeight="600" fill="rgb(var(--text))">{n.name}</text>
        </g>)}
      </svg>
    </div>
    <div className="graph-caption" aria-live="polite"><span className="graph-caption-icon" aria-hidden="true">↗</span><div><h3 className="text-sm font-bold">{node.name}</h3><p className="mt-1 text-xs leading-relaxed text-ink-soft">{node.description}</p></div></div>
    <p className="px-5 pb-4 text-[11px] text-ink-faint">Select a node · Connections show example learning relationships, not your assessment.</p>
  </div>;
}
