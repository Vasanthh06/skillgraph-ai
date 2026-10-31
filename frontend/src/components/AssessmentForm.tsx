import { useState } from "react";
import { Link } from "react-router-dom";
import { Card, ErrorNote, Loading, NeedsSetup, Tag } from "./ui";
import { CalibrationBadge } from "./IntelligencePanels";
import SaveBar from "./SaveBar";
import { useAction, useGet } from "../hooks/useApi";
import { http } from "../services/api";
import { useDirtyFlag } from "../store/dirty";
import type { Json } from "../types/api";

type Checks = Record<string, boolean>;
const sameChecks = (a: Checks, b: Checks) => Object.keys({ ...a, ...b }).every((k) => !!a[k] === !!b[k]);

/**
 * Role-specific assessment. Edits are a DRAFT that holds only what the user changed (layered over what is saved),
 * so it can never go stale or overwrite something saved elsewhere. Nothing is applied until Save.
 */
export default function AssessmentForm({ onSaved, saveLabel = "Save assessment", onBack }: { onSaved?: () => void; saveLabel?: string; onBack?: () => void }) {
  const form = useGet<Json>("/assessment");
  const [levels, setLevels] = useState<Record<string, string>>({});   // skill -> level, only where it differs from saved
  const [confs, setConfs] = useState<Record<string, number>>({});    // skill -> explicit confidence, only where it differs
  const [checks, setChecks] = useState<Record<string, Checks>>({});   // skill -> full checklist, only where it differs from saved
  const [open, setOpen] = useState<string | null>(null);
  const save = useAction((answers: Json[]) => http.post<Json>("/assessment", { answers }), "Assessment saved. Your readiness, gaps and roadmap have been recalculated.");

  const skills: Json[] = (form.data?.groups ?? []).flatMap((g: Json) => g.skills);
  const bySlug: Record<string, Json> = Object.fromEntries(skills.map((s) => [s.slug, s]));
  const savedChecks = (s: Json): Checks => Object.fromEntries(s.checklist.map((x: Json) => [x.label, !!x.checked]));

  const changedSkills = new Set<string>([
    ...Object.keys(levels).filter((k) => levels[k] !== (bySlug[k]?.self_level ?? undefined)),
    ...Object.keys(confs).filter((k) => confs[k] !== (bySlug[k]?.confidence_rating ?? undefined)),
    ...Object.keys(checks).filter((k) => bySlug[k] && !sameChecks(checks[k], savedChecks(bySlug[k]))),
  ]);
  const count = changedSkills.size;
  useDirtyFlag("/assessment", "Assessment", count > 0);

  if (form.isLoading) return <Loading what="Building your assessment" />;
  if (form.error) return <ErrorNote error={form.error} />;
  if (form.data.needs) return <NeedsSetup needs={form.data.needs} />;

  const setLevel = (s: Json, v: string) => setLevels((p) => {
    const n = { ...p };
    if (v === (s.self_level ?? undefined)) delete n[s.slug]; else n[s.slug] = v;
    return n;
  });
  const setConf = (s: Json, v: number) => setConfs((p) => {
    const n = { ...p };
    if (v === (s.confidence_rating ?? undefined)) delete n[s.slug]; else n[s.slug] = v;
    return n;
  });
  const setCheck = (s: Json, label: string, on: boolean) => setChecks((p) => {
    const next = { ...(p[s.slug] ?? savedChecks(s)), [label]: on };
    const n = { ...p };
    if (sameChecks(next, savedChecks(s))) delete n[s.slug]; else n[s.slug] = next;
    return n;
  });
  const discard = () => { setLevels({}); setConfs({}); setChecks({}); };
  const submit = () => {
    const answers = [...changedSkills].map((slug) => ({ skill: slug, level: levels[slug] ?? null, confidence: confs[slug] ?? null, checklist: checks[slug] ?? null }));
    save.mutate(answers, { onSuccess: () => { discard(); onSaved?.(); } });
  };

  return (
    <div>
      <h2 className="text-xl font-bold">Let's understand what you already know</h2>
      <p className="mt-1 text-sm text-ink-soft">
        Questions come from the {form.data.role} skill map. <b>Nothing is applied until you press Save.</b> Unverified claims are capped until a quiz, project or resume backs them up.
      </p>
      <p className="mt-1 text-sm text-ink-soft">For each skill, also set how confident you are <em>before</em> any check. Later, scored practice is compared with that rating — the two are always kept separate from your blended estimate.</p>
      {form.data.methodology?.calibration && (
        <details className="mt-2 text-sm text-ink-soft"><summary className="cursor-pointer font-medium text-ink">How confidence calibration works</summary><p className="mt-1">{form.data.methodology.calibration}</p></details>
      )}
      {form.data.groups.map((g: Json) => (
        <fieldset key={g.name} className="mt-8">
          <legend className="font-display text-lg font-bold">{g.name}</legend>
          <ul className="mt-3 space-y-3">
            {g.skills.map((s: Json) => {
              const level = levels[s.slug] ?? s.self_level;
              const conf = confs[s.slug] ?? s.confidence_rating ?? s.calibration?.self_rating ?? 50;
              const cal = s.calibration;
              const view = checks[s.slug] ?? savedChecks(s);
              return (
                <li key={s.slug}>
                  <Card>
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span className="font-medium">
                        {s.name} {!s.required && <Tag>Optional</Tag>} {s.resume_evidence && <Tag tone="good">On your resume</Tag>} {changedSkills.has(s.slug) && <Tag tone="demo">Unsaved</Tag>}
                      </span>
                      {s.checklist.length > 0 && <button type="button" className="text-sm text-route underline" onClick={() => setOpen(open === s.slug ? null : s.slug)}>{open === s.slug ? "Hide topics" : "Tick topics"}</button>}
                    </div>
                    <div role="radiogroup" aria-label={`${s.name} comfort level`} className="mt-3 flex flex-wrap gap-2">
                      {form.data.levels.map((lv: Json) => (
                        <label key={lv.value} className={`cursor-pointer rounded-md border px-3 py-1 text-sm ${level === lv.value ? "border-route bg-route-tint font-semibold text-route-dark" : "border-mist"}`}>
                          <input type="radio" className="sr-only" name={s.slug} checked={level === lv.value} onChange={() => setLevel(s, lv.value)} />
                          {lv.label}
                        </label>
                      ))}
                    </div>
                    <div className="mt-3 flex flex-wrap items-center gap-3">
                      <label htmlFor={`conf-${s.slug}`} className="text-sm font-medium">How confident are you that you could use this independently?</label>
                      <input id={`conf-${s.slug}`} type="range" min={0} max={100} step={5} value={conf} aria-describedby={`conf-help-${s.slug}`}
                        onChange={(e) => setConf(s, Number(e.target.value))} />
                      <output htmlFor={`conf-${s.slug}`} className="text-sm font-bold tabular-nums">{conf}%</output>
                      <span id={`conf-help-${s.slug}`} className="text-xs text-ink-faint">{s.confidence_rating === null && confs[s.slug] === undefined ? "Not saved yet — move the slider, then Save." : "Saved separately from scored practice."}</span>
                    </div>
                    {cal && (
                      <div className="mt-3 rounded-lg border border-mist p-3">
                        <div className="flex flex-wrap items-center gap-2"><CalibrationBadge cal={cal} /><span className="text-xs text-ink-faint">Estimate {cal.estimate_score}% · your rating {cal.self_rating === null ? "—" : `${cal.self_rating}%`} · recent scored practice {cal.demonstrated_score === null ? "not enough yet" : `${cal.demonstrated_score}%`}</span></div>
                        <p className="mt-1 text-sm text-ink-soft">{cal.reason}</p>
                        {cal.missed_topics?.length > 0 && <p className="mt-1 text-xs text-ink-faint">To revisit: {cal.missed_topics.join("; ")}</p>}
                        <Link to={cal.action.route} className="mt-2 inline-block text-sm text-route underline">{cal.action.label} →</Link>
                      </div>
                    )}
                    {open === s.slug && (
                      <div className="mt-3 grid gap-1 sm:grid-cols-2">
                        {s.checklist.map((c: Json) => (
                          <label key={c.label} className="flex items-center gap-2 text-sm">
                            <input type="checkbox" checked={!!view[c.label]} onChange={(e) => setCheck(s, c.label, e.target.checked)} />
                            {c.label}
                          </label>
                        ))}
                      </div>
                    )}
                  </Card>
                </li>
              );
            })}
          </ul>
        </fieldset>
      ))}
      <SaveBar count={count} saving={save.isPending} onSave={submit} onDiscard={discard} saveLabel={saveLabel} error={(save.error as Error | null)?.message} />
      {onBack && <button type="button" className="btn-quiet mt-3" onClick={onBack}>Back</button>}
    </div>
  );
}
