import { useEffect, useState } from "react";
import { Bar, Card, ErrorNote, Loading, Section, Tag } from "./ui";
import SaveBar from "./SaveBar";
import { useAction, useGet } from "../hooks/useApi";
import { http } from "../services/api";
import { useReducedMotion } from "../hooks/useMotion";
import { useDirtyFlag } from "../store/dirty";
import type { Json } from "../types/api";

/**
 * Two steps: uploading STAGES a resume for review; it only feeds the profile once the user presses Save.
 * The user can leave out skills that were detected wrongly before saving.
 */
export default function ResumePanel() {
  const { data: r, isLoading, error } = useGet<Json>("/resume");
  const [excluded, setExcluded] = useState<Set<string>>(new Set());
  const stage = useAction((f: File) => http.upload<Json>("/resume/upload", f));
  const confirm = useAction((exclude: string[]) => http.post<Json>("/resume/confirm", { exclude }), "Resume saved. Your skills and readiness have been recalculated.");
  const discard = useAction(() => http.del<void>("/resume/pending"), "Uploaded resume discarded. Nothing was changed.");
  const remove = useAction(() => http.del<void>("/resume"), "Saved resume removed. Your profile was recalculated without it.");

  const reduced = useReducedMotion();
  // Presentation only: the analysis is already done when the file is staged. The scan reveals real results; it can be skipped,
  // and users who prefer reduced motion never see it.
  const [scanning, setScanning] = useState(false);
  useEffect(() => {
    if (!scanning) return;
    const t = window.setTimeout(() => setScanning(false), 1800);
    return () => window.clearTimeout(t);
  }, [scanning]);
  const pending: Json | null = r?.pending ?? null;
  useDirtyFlag("/resume", "Resume", !!pending);
  if (isLoading) return <Loading />;
  if (error) return <ErrorNote error={error} />;

  const toggle = (slug: string) => setExcluded((p) => { const n = new Set(p); if (n.has(slug)) n.delete(slug); else n.add(slug); return n; });
  const a = r.analysis;

  return (
    <div>
      <label htmlFor="cv" className="btn cursor-pointer">{r.uploaded || pending ? "Upload a different resume" : "Upload resume"}</label>
      <input id="cv" type="file" accept=".pdf,.docx,.txt" className="sr-only"
        onChange={(e) => { const f = e.target.files?.[0]; if (f) { setExcluded(new Set()); stage.mutate(f, { onSuccess: () => { if (!reduced) setScanning(true); } }); } e.target.value = ""; }} />
      <span className="ml-3 text-sm text-ink-faint">PDF, DOCX or TXT, up to 5 MB</span>
      {stage.isPending && <Loading what="Reading your resume" />}
      {stage.error && <div className="mt-3"><ErrorNote error={stage.error} /></div>}

      {pending && scanning && (
        <Card className="mt-6">
          <div role="status" aria-live="polite" className="grid items-center gap-5 sm:grid-cols-[9.5rem_1fr]">
            <div aria-hidden className="relative h-48 overflow-hidden rounded-lg border border-mist bg-inset/70 p-3">
              <div className="scanline" />
              {Array.from({ length: 14 }).map((_, i) => <i key={i} className="my-2 block h-1.5 rounded bg-glow-blue/20" style={{ width: i % 3 === 0 ? "70%" : i % 4 === 0 ? "55%" : "100%" }} />)}
            </div>
            <div>
              <h2 className="text-xl font-bold">Analysis complete: revealing results</h2>
              <p className="mt-1 text-sm text-ink-soft">Your file has been read. Showing what was found.</p>
              <ol className="my-3 space-y-1 text-sm text-ink-soft">
                <li className="scan-step" style={{ "--d": "0s" } as React.CSSProperties}>✓ Read {pending.filename}</li>
                <li className="scan-step" style={{ "--d": ".5s" } as React.CSSProperties}>✓ Found {pending.extracted.skills.length} skill{pending.extracted.skills.length === 1 ? "" : "s"}</li>
                <li className="scan-step" style={{ "--d": "1s" } as React.CSSProperties}>✓ {pending.role ? `Matched against ${pending.role}` : "Choose a target role to see the match"}</li>
              </ol>
              <button type="button" className="btn-quiet px-3 py-1 text-xs" onClick={() => setScanning(false)}>Skip animation</button>
            </div>
          </div>
        </Card>
      )}

      {pending && !scanning && (
        <>
          <Card className="mt-6 border-2 border-signal">
            <h2 className="text-xl font-bold">Review before saving</h2>
            <p className="mt-1 text-sm text-ink-soft">Found in <b>{pending.filename}</b>. Click a skill to leave it out if it was detected wrongly. Nothing is added to your profile until you press <b>Save resume</b>.</p>
            <p className="mt-3 flex flex-wrap gap-2">
              {pending.extracted.skills.map((s: Json, ix: number) => (
                <button key={s.slug} type="button" aria-pressed={!excluded.has(s.slug)} onClick={() => toggle(s.slug)} style={{ "--i": ix } as React.CSSProperties}
                  className={`reveal rounded-md border px-2 py-1 text-sm ${excluded.has(s.slug) ? "border-dashed border-mist bg-fog text-ink-faint line-through" : s.evidence === "applied" ? "border-moss bg-green-50 text-moss" : "border-mist bg-white"}`}>
                  {excluded.has(s.slug) ? "✗ " : ""}{s.name}
                </button>
              ))}
            </p>
            <p className="mt-2 text-xs text-ink-faint">Green: used in a project or role. Grey: only listed. Crossed out: will be left out.</p>
            {pending.analysis && (<>
              <p className="mt-3 text-sm">If saved, your match for {pending.role} is <b>{pending.analysis.role_match}%</b> and ATS checks <b>{pending.analysis.ats_score}%</b>.</p>
              <div className="mt-3 grid gap-3 text-sm sm:grid-cols-2">
                <div><h3 className="font-bold">Matched skills</h3><p className="mt-1 flex flex-wrap gap-1.5">{pending.analysis.found_keywords.map((x: string, i: number) => <span key={x} className="reveal rounded-md border border-moss/40 bg-green-50 px-2 py-0.5 text-xs text-moss" style={{ "--i": i } as React.CSSProperties}>{x}</span>)}{pending.analysis.found_keywords.length === 0 && <span className="text-ink-faint">None</span>}</p></div>
                <div><h3 className="font-bold">Missing keywords</h3><p className="mt-1 flex flex-wrap gap-1.5">{pending.analysis.missing_keywords.map((x: string, i: number) => <span key={x} className="reveal rounded-md border border-alert/40 bg-red-50 px-2 py-0.5 text-xs text-alert" style={{ "--i": i } as React.CSSProperties}>{x}</span>)}{pending.analysis.missing_keywords.length === 0 && <span className="text-moss">None missing</span>}</p></div>
              </div>
            </>)}
          </Card>
          <SaveBar count={1} saving={confirm.isPending || discard.isPending} saveLabel="Save resume"
            onSave={() => confirm.mutate([...excluded], { onSuccess: () => setExcluded(new Set()) })}
            onDiscard={() => discard.mutate(undefined as never, { onSuccess: () => setExcluded(new Set()) })}
            error={((confirm.error ?? discard.error) as Error | null)?.message} />
        </>
      )}

      {!r.uploaded && !pending && <p className="mt-6 text-ink-soft">No resume saved yet. Your skill profile currently uses your self-assessment only.</p>}
      {r.uploaded && (
        <>
          <p className="mt-6 flex flex-wrap items-center gap-3 text-sm text-ink-soft">Saved resume: <b>{r.filename}</b>{r.role && <> · compared with {r.role}</>}
            <button type="button" className="text-route underline" disabled={remove.isPending} onClick={() => remove.mutate(undefined as never)}>Remove saved resume</button></p>
          {a && (
            <div className="mt-4 grid gap-4 sm:grid-cols-2">
              <Card><p className="text-sm text-ink-faint">Resume match for {r.role}</p><p className="font-display text-4xl font-bold">{a.role_match}%</p><Bar value={a.role_match} label="Resume match" /></Card>
              <Card><p className="text-sm text-ink-faint">ATS readiness checks</p><p className="font-display text-4xl font-bold">{a.ats_score}%</p><Bar value={a.ats_score} tone="moss" label="ATS" /></Card>
            </div>
          )}
          <Section title="Skills we found">
            <p className="flex flex-wrap gap-2">{r.extracted.skills.map((s: Json) => <Tag key={s.slug} tone={s.evidence === "applied" ? "good" : "plain"}>{s.name}{s.written_as.some((w: string) => w.toLowerCase() !== s.name.toLowerCase()) && ` (written: ${s.written_as.join(", ")})`}</Tag>)}</p>
            <p className="mt-2 text-xs text-ink-faint">Green: used in a project or role. Grey: only listed.</p>
            {r.extracted.soft_skills.length > 0 && <p className="mt-2 text-sm">Soft skills: {r.extracted.soft_skills.join(", ")}</p>}
            {r.extracted.education.length > 0 && <p className="text-sm">Education: {r.extracted.education.join(", ")}</p>}
            {r.extracted.certifications.length > 0 && <p className="text-sm">Certifications: {r.extracted.certifications.join("; ")}</p>}
          </Section>
          {a && (
            <Section title="Role match: matched and missing skills">
              <div className="grid gap-4 sm:grid-cols-2">
                <Card><h3 className="font-bold">Matched skills</h3><p className="mt-2 flex flex-wrap gap-1.5">{a.found_keywords.map((x: string) => <Tag key={x} tone="good">{x}</Tag>)}{a.found_keywords.length === 0 && <span className="text-sm text-ink-faint">None yet</span>}</p></Card>
                <Card><h3 className="font-bold">Missing keywords</h3><p className="mt-2 flex flex-wrap gap-1.5">{a.missing_keywords.map((x: string) => <Tag key={x} tone="warn">{x}</Tag>)}{a.missing_keywords.length === 0 && <span className="text-sm text-moss">None missing</span>}</p><p className="mt-2 text-xs text-ink-faint">Add only skills you genuinely have.</p></Card>
              </div>
            </Section>
          )}
          {a && (
            <>
              <Section title="Checks"><ul className="space-y-1 text-sm">{a.checks.map((c: Json) => <li key={c.name}>{c.ok ? "✓" : "✗"} <strong>{c.name}</strong>: {c.detail}</li>)}</ul></Section>
              {a.evidence_gaps.length > 0 && <Section title="Missing evidence"><ul className="space-y-2 text-sm">{a.evidence_gaps.map((g: Json) => <li key={g.skill}><strong>{g.skill}:</strong> {g.suggestion}</li>)}</ul></Section>}
              {a.tips.length > 0 && <Section title="Improvements"><ul className="list-disc space-y-2 pl-5 text-sm">{a.tips.map((t: string) => <li key={t}>{t}</li>)}</ul></Section>}
            </>
          )}
        </>
      )}
    </div>
  );
}
