import { useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { AnimatedNumber } from "../components/dashboard";
import { Card, DemoTag, EmptyState, ErrorNote, NeedsSetup, PageSkeleton, PageTitle, Seg, Tag } from "../components/ui";
import { useAction, useGet } from "../hooks/useApi";
import { http } from "../services/api";
import type { Json } from "../types/api";

type Diff = "" | "beginner" | "intermediate" | "advanced";
const STATUS: [string, string][] = [["planned", "Plan it"], ["in_progress", "Start"], ["completed", "Completed"]];
const NONE = { diff: "" as Diff, ready: false, skill: "", status: "" };

export default function Projects() {
  const { data, isLoading, error, refetch } = useGet<Json>("/projects");
  const [params] = useSearchParams();
  const [f, setF] = useState(NONE);
  const [open, setOpen] = useState<string | null>(params.get("open"));
  const setStatus = useAction((v: { key: string; status: string }) => http.post<Json>(`/projects/${v.key}/status`, { status: v.status }), "Saved: project status updated.");

  const all: Json[] = data?.projects ?? [];
  const skills = useMemo(() => {
    const m = new Map<string, string>();
    all.forEach((p) => p.gains.forEach((s: string, i: number) => m.set(s, p.gains_names[i])));
    return [...m.entries()].sort((a, b) => (a[1] < b[1] ? -1 : 1));
  }, [all]);
  const rows = all.filter((p) => (!f.diff || p.difficulty === f.diff) && (!f.ready || p.ready) && (!f.skill || p.gains.includes(f.skill)) && (!f.status || p.status === f.status));

  if (isLoading) return <PageSkeleton />;
  if (error || !data) return <ErrorNote error={error} onRetry={() => refetch()} />;
  const done = all.filter((p) => p.status === "completed").length;
  const started = all.filter((p) => p.status === "in_progress").length;
  const filtered = JSON.stringify(f) !== JSON.stringify(NONE);

  return (
    <div className="max-w-4xl">
      <PageTitle title="Project Recommendations" sub="Projects that build the skills you still need. Finished projects count as evidence for those skills." />
      <p className="mb-5 flex items-center gap-2 text-sm text-ink-soft"><DemoTag what="Demo projects" /> Curated suggestions, not generated.</p>
      {data.needs ? <NeedsSetup needs={data.needs} /> : (
        <>
          <div className="mb-5 grid gap-4 md:grid-cols-3">
            <Card><small className="text-ink-faint">Completed</small><p className="font-display text-4xl font-bold"><AnimatedNumber value={done} /></p></Card>
            <Card><small className="text-ink-faint">In progress</small><p className="font-display text-4xl font-bold"><AnimatedNumber value={started} /></p></Card>
            <Card><small className="text-ink-faint">Evidence from projects</small><p className="mt-2 font-display text-xl font-bold">{done ? "Counting toward your skills" : "None yet"}</p></Card>
          </div>

          <div className="mb-3 flex flex-wrap items-center gap-3">
            <Seg<Diff> label="Filter by difficulty" value={f.diff} onChange={(v) => setF({ ...f, diff: v })} options={[{ value: "", label: "All levels" }, { value: "beginner", label: "Beginner" }, { value: "intermediate", label: "Intermediate" }, { value: "advanced", label: "Advanced" }]} />
            <label className="flex items-center gap-1.5 text-sm text-ink-soft"><input type="checkbox" checked={f.ready} onChange={(e) => setF({ ...f, ready: e.target.checked })} /> Ready to start</label>
            <label className="sr-only" htmlFor="pskill">Builds skill</label>
            <select id="pskill" className="field w-auto" value={f.skill} onChange={(e) => setF({ ...f, skill: e.target.value })}><option value="">Builds any skill</option>{skills.map(([slug, name]) => <option key={slug} value={slug}>{name}</option>)}</select>
            <label className="sr-only" htmlFor="pstatus">Status</label>
            <select id="pstatus" className="field w-auto" value={f.status} onChange={(e) => setF({ ...f, status: e.target.value })}>{[["", "Any status"], ["not_started", "Not started"], ["planned", "Planned"], ["in_progress", "In progress"], ["completed", "Completed"]].map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select>
            {filtered && <button type="button" className="btn-quiet px-3 py-1 text-xs" onClick={() => setF(NONE)}>Clear filters</button>}
          </div>
          <p className="mb-3 text-sm text-ink-faint" aria-live="polite">{rows.length} of {all.length} projects</p>

          {rows.length === 0 ? (
            <EmptyState title="No projects match" action={<button type="button" className="btn-quiet px-3 py-1" onClick={() => setF(NONE)}>Clear filters</button>}>Try a different level or clear the filters.</EmptyState>
          ) : (
            <ul className="space-y-4">
              {rows.map((p) => {
                const isOpen = open === p.key;
                return (
                  <li key={p.key}>
                    <Card lift>
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div><h3 className="font-display text-lg font-bold">{p.title}</h3><p className="text-sm text-ink-faint">~{p.hours}h</p></div>
                        <p className="flex flex-wrap gap-1.5"><Tag>{p.difficulty}</Tag>{p.recommended && <Tag tone="good">For your gaps</Tag>}{p.status !== "not_started" && <Tag tone="demo">{p.status.replace("_", " ")}</Tag>}</p>
                      </div>
                      <p className="mt-2 text-sm text-ink-soft">{p.why}</p>
                      <p className="mt-2 flex flex-wrap gap-1.5 text-xs">
                        {p.gains_names.map((n: string) => <span key={n} className="rounded-md border border-moss/40 bg-green-50 px-2 py-0.5 text-moss">Builds {n}</span>)}
                        {p.missing_prerequisites.map((n: string) => <span key={n} className="rounded-md border border-alert/40 bg-red-50 px-2 py-0.5 text-alert">Needs {n}</span>)}
                      </p>
                      <div className="mt-3 flex flex-wrap gap-2">
                        <button type="button" className="btn-quiet px-3 py-1 text-xs" aria-expanded={isOpen} onClick={() => setOpen(isOpen ? null : p.key)}>{isOpen ? "Hide details" : "View details"}</button>
                        {STATUS.map(([v, l]) => (
                          <button key={v} type="button" aria-pressed={p.status === v} disabled={setStatus.isPending} onClick={() => setStatus.mutate({ key: p.key, status: v })}
                            className={`px-3 py-1 text-xs ${p.status === v ? "btn-quiet border-moss/50 text-moss" : "btn-quiet"}`}>{p.status === v ? `${l} ✓` : l}</button>
                        ))}
                        {!p.ready && <Link to={`/learn?skill=${p.missing_slugs[0]}`} className="btn-quiet px-3 py-1 text-xs">Learn {p.missing_prerequisites[0]} first</Link>}
                      </div>
                      {isOpen && (
                        <div className="mt-3 space-y-1 border-t border-mist pt-3 text-sm">
                          <p>{p.description}</p>
                          <p><b>You will need:</b> {p.requires_names.map((n: string) => `${p.missing_prerequisites.includes(n) ? "✗" : "✓"} ${n}`).join(" · ")}</p>
                          <p><b>Expected output:</b> {p.expected_output}</p>
                          <p><b>Portfolio value:</b> {p.portfolio_value}</p>
                        </div>
                      )}
                    </Card>
                  </li>
                );
              })}
            </ul>
          )}
        </>
      )}
    </div>
  );
}
