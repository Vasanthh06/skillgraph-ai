import { useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { Bar, Card, DemoTag, EmptyState, ErrorNote, NeedsSetup, PageSkeleton, PageTitle, Section, Tag } from "../components/ui";
import { useAction, useGet } from "../hooks/useApi";
import { http } from "../services/api";
import type { Json } from "../types/api";

type Sort = "match" | "company" | "title";
interface Filters { q: string; min: number; exp: string; loc: string; status: string; sort: Sort }
const NONE: Filters = { q: "", min: 0, exp: "", loc: "", status: "", sort: "match" };

export default function Jobs() {
  const { data, isLoading, error, refetch } = useGet<Json>("/jobs");
  const profile = useGet<Json>("/profile");
  const [params] = useSearchParams();
  const nav = useNavigate();
  const [f, setF] = useState<Filters>(NONE);
  const [open, setOpen] = useState<string | null>(params.get("open"));
  const [jd, setJd] = useState(false);
  const [text, setText] = useState("");
  const analyze = useAction((t: string) => http.post<Json>("/jobs/analyze", { text: t }));
  const setStatus = useAction((v: { key: string; status: string }) => http.post<Json>(`/jobs/${v.key}/status`, { status: v.status }), "Saved.");
  const clearStatus = useAction((key: string) => http.del<void>(`/jobs/${key}/status`), "Removed from saved jobs.");

  const city = (profile.data?.location ?? "").toLowerCase();
  const all: Json[] = data?.jobs ?? [];
  const rows = useMemo(() => {
    const ql = f.q.trim().toLowerCase();
    const out = all.filter((j) => (!ql || `${j.title} ${j.company}`.toLowerCase().includes(ql)) && j.match >= f.min && (!f.exp || j.experience === f.exp)
      && (!f.loc || (f.loc === "remote" ? j.location.toLowerCase() === "remote" : !!city && j.location.toLowerCase().includes(city)))
      && (!f.status || j.application_status === f.status));
    if (f.sort === "company") out.sort((a, b) => (a.company < b.company ? -1 : 1));
    if (f.sort === "title") out.sort((a, b) => (a.title < b.title ? -1 : 1));
    return out;
  }, [all, f, city]);

  if (isLoading) return <PageSkeleton />;
  if (error || !data) return <ErrorNote error={error} onRetry={() => refetch()} />;
  const filtered = JSON.stringify(f) !== JSON.stringify(NONE);
  const set = <K extends keyof Filters>(k: K, v: Filters[K]) => setF((p) => ({ ...p, [k]: v }));
  const busy = setStatus.isPending || clearStatus.isPending;
  const err = (setStatus.error ?? clearStatus.error) as Error | null;

  const save = (j: Json) => (j.application_status === "applied" ? undefined : j.application_status === "saved" ? clearStatus.mutate(j.key) : setStatus.mutate({ key: j.key, status: "saved" }));
  const apply = (j: Json) => setStatus.mutate({ key: j.key, status: j.application_status === "applied" ? "saved" : "applied" });

  return (
    <div className="max-w-4xl">
      <PageTitle title="Job Matching" sub="Matched to your actual skills, with the reasoning shown." />
      <p className="mb-5 flex items-center gap-2 text-sm text-ink-soft"><DemoTag what="Demo listings" /> Sample listings from fictional companies, not live vacancies.</p>
      {data.needs ? <NeedsSetup needs={data.needs} /> : (
        <>
          <div className="mb-3 flex flex-wrap items-center gap-2">
            <label className="sr-only" htmlFor="jq">Search jobs</label>
            <input id="jq" type="search" className="field w-auto min-w-[12rem]" placeholder="Search title or company" value={f.q} onChange={(e) => set("q", e.target.value)} />
            <label className="sr-only" htmlFor="jmin">Minimum match</label>
            <select id="jmin" className="field w-auto" value={f.min} onChange={(e) => set("min", Number(e.target.value))}>{[[0, "Any match"], [50, "50%+ match"], [70, "70%+ match"], [85, "85%+ match"]].map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select>
            <label className="sr-only" htmlFor="jexp">Experience</label>
            <select id="jexp" className="field w-auto" value={f.exp} onChange={(e) => set("exp", e.target.value)}>{[["", "Any experience"], ["fresher", "Fresher"], ["0-1", "0–1 years"], ["1-3", "1–3 years"]].map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select>
            <label className="sr-only" htmlFor="jloc">Location</label>
            <select id="jloc" className="field w-auto" value={f.loc} onChange={(e) => set("loc", e.target.value)}><option value="">Any location</option><option value="remote">Remote</option><option value="mine">{profile.data?.location ? `Near ${profile.data.location}` : "Near me"}</option></select>
            <label className="sr-only" htmlFor="jst">Status</label>
            <select id="jst" className="field w-auto" value={f.status} onChange={(e) => set("status", e.target.value)}><option value="">All jobs</option><option value="saved">Saved</option><option value="applied">Applied</option></select>
            <label className="sr-only" htmlFor="jsort">Sort</label>
            <select id="jsort" className="field w-auto" value={f.sort} onChange={(e) => set("sort", e.target.value as Sort)}><option value="match">Best match</option><option value="company">Company A–Z</option><option value="title">Title A–Z</option></select>
            {filtered && <button type="button" className="btn-quiet px-3 py-1 text-xs" onClick={() => setF(NONE)}>Clear filters</button>}
          </div>
          <p className="mb-3 text-sm text-ink-faint" aria-live="polite">{rows.length} of {all.length} jobs</p>
          {err && <div className="mb-3"><ErrorNote error={err} /></div>}

          {rows.length === 0 ? (
            <EmptyState title="No jobs match these filters" action={<button type="button" className="btn-quiet px-3 py-1" onClick={() => setF(NONE)}>Clear filters</button>}>Loosen a filter or clear them all to see every listing.</EmptyState>
          ) : (
            <ul className="space-y-4">
              {rows.map((j) => {
                const st: string | null = j.application_status;
                const isOpen = open === j.key;
                return (
                  <li key={j.key}>
                    <Card lift>
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div><h3 className="font-display text-lg font-bold">{j.title}</h3><p className="text-sm text-ink-faint">{j.company} · {j.location} · {j.experience === "fresher" ? "Fresher" : `${j.experience} yrs`}</p></div>
                        <p className="font-display text-3xl font-bold" aria-label={`${j.match}% match`}>{j.match}%</p>
                      </div>
                      <div className="mt-2"><Bar value={j.match} tone="moss" label={`${j.title} match`} /></div>
                      <p className="mt-2 text-sm">{j.explanation}</p>
                      <p className="mt-2 flex flex-wrap gap-1.5 text-xs">
                        {j.missing.length ? j.missing.slice(0, 3).map((m: string) => <span key={m} className="rounded-md border border-alert/40 bg-red-50 px-2 py-0.5 text-alert">Missing: {m}</span>) : <span className="rounded-md border border-moss/40 bg-green-50 px-2 py-0.5 text-moss">No required skills missing</span>}
                      </p>
                      <div className="mt-3 flex flex-wrap gap-2">
                        <button type="button" className="btn-quiet px-3 py-1 text-xs" aria-expanded={isOpen} onClick={() => setOpen(isOpen ? null : j.key)}>{isOpen ? "Hide details" : "View details"}</button>
                        <button type="button" disabled={busy} className={`px-3 py-1 text-xs ${st ? "btn-quiet border-moss/50 text-moss" : "btn"}`} onClick={() => save(j)}>{st === "applied" ? "Applied ✓" : st === "saved" ? "Saved ✓ (click to remove)" : "Save job"}</button>
                        <button type="button" disabled={busy} className="btn-quiet px-3 py-1 text-xs" onClick={() => apply(j)}>{st === "applied" ? "Undo applied" : "Mark applied"}</button>
                        <button type="button" className="btn-quiet px-3 py-1 text-xs" onClick={() => nav("/interview", { state: { jobKey: j.key } })}>Prep interview</button>
                      </div>
                      {isOpen && (
                        <div className="mt-3 grid gap-4 border-t border-mist pt-3 text-sm md:grid-cols-2">
                          <div><h4 className="font-bold">Why {j.match}%</h4><ul className="mt-1 text-ink-soft"><li>Skills: {j.components.skills}%</li><li>Role fit: {j.components.role}%</li><li>Experience: {j.components.experience}%</li><li>Location: {j.components.location}%</li></ul></div>
                          <div><h4 className="font-bold">Your skills for this job</h4><p className="mt-1 flex flex-wrap gap-1.5 text-xs">{j.have.map((x: string) => <Tag key={x} tone="good">{x}</Tag>)}{j.weak.map((x: string) => <Tag key={x}>{x} (partial)</Tag>)}{j.missing.map((x: string) => <Tag key={x} tone="warn">{x}</Tag>)}</p></div>
                          {j.before_applying.length > 0 && <p className="text-ink-soft md:col-span-2">Before applying: {j.before_applying.join("; ")}</p>}
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

      <Section title="Analyse a job description">
        <button type="button" className="btn-quiet" aria-expanded={jd} onClick={() => setJd(!jd)}>{jd ? "Hide" : "Paste a job description"}</button>
        {jd && (
          <div className="mt-3">
            <label htmlFor="jdtext" className="label">Job description</label>
            <textarea id="jdtext" className="field h-40" value={text} onChange={(e) => setText(e.target.value)} placeholder="Paste the full job description…" />
            <button type="button" className="btn mt-3" disabled={text.trim().length < 30 || analyze.isPending} onClick={() => analyze.mutate(text)}>{analyze.isPending ? "Analysing…" : "Analyse"}</button>
            {analyze.error && <div className="mt-3"><ErrorNote error={analyze.error} /></div>}
            {analyze.data && (
              <Card className="mt-4">
                <p className="font-display text-3xl font-bold">{analyze.data.match}% match</p>
                <div className="mt-3 grid gap-3 text-sm sm:grid-cols-3">
                  <div><h4 className="font-bold">Strong</h4>{analyze.data.strong.join(", ") || "None"}</div>
                  <div><h4 className="font-bold">Weak</h4>{analyze.data.weak.join(", ") || "None"}</div>
                  <div><h4 className="font-bold">Missing</h4>{analyze.data.missing.join(", ") || "None"}</div>
                </div>
                <p className="mt-3 text-sm"><b>Required:</b> {analyze.data.required_skills.join(", ") || "none detected"}<br /><b>Preferred:</b> {analyze.data.preferred_skills.join(", ") || "none detected"}</p>
                <Link to="/interview" state={{ jd: text }} className="mt-3 inline-block text-sm text-route underline">Practise interview questions for this job</Link>
              </Card>
            )}
          </div>
        )}
      </Section>
    </div>
  );
}
