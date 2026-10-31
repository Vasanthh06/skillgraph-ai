import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import type { Json } from "../types/api";

export const pct = (n: number | null | undefined) => (n === null || n === undefined ? "–" : `${Math.round(n)}%`);

export function PageTitle({ title, sub }: { title: string; sub?: ReactNode }) {
  return (
    <header className="mb-8">
      <h1 className="text-3xl font-bold">{title}</h1>
      {sub && <p className="mt-2 max-w-2xl text-ink-soft">{sub}</p>}
    </header>
  );
}

export function Section({ title, children, aside }: { title: string; children: ReactNode; aside?: ReactNode }) {
  return (
    <section className="mt-10">
      <div className="flex items-baseline justify-between gap-4">
        <h2 className="text-xl font-bold">{title}</h2>
        {aside}
      </div>
      <div className="mt-4">{children}</div>
    </section>
  );
}

export function Bar({ value, label, tone = "route" }: { value: number | null; label?: string; tone?: "route" | "moss" | "signal" }) {
  const color = tone === "moss"
    ? "bg-gradient-to-r from-emerald-500 to-glow-cyan shadow-[0_0_12px_rgba(52,211,153,0.7)]"
    : tone === "signal"
      ? "bg-gradient-to-r from-amber-500 to-signal shadow-[0_0_12px_rgba(251,191,36,0.6)]"
      : "bg-brand shadow-[0_0_12px_rgba(124,92,255,0.8)]";
  return (
    <div className="flex items-center gap-3" role="img" aria-label={`${label ?? "progress"}: ${pct(value)}`}>
      <div className="h-2 flex-1 overflow-hidden rounded-full bg-mist/70">
        <div className={`bar-fill h-2 rounded-full transition-[width] duration-700 ${color}`} style={{ width: `${Math.max(0, Math.min(100, value ?? 0))}%` }} />
      </div>
      <span className="w-10 text-right text-sm tabular-nums text-ink-soft">{pct(value)}</span>
    </div>
  );
}

export function Tag({ children, tone = "plain" }: { children: ReactNode; tone?: "plain" | "demo" | "warn" | "good" | "generated" }) {
  const cls = { plain: "bg-mist text-ink-soft", demo: "bg-signal/25 text-ink", warn: "bg-red-100 text-alert", good: "bg-green-100 text-moss", generated: "bg-route-tint text-route-dark" }[tone];
  return <span className={`inline-block rounded px-2 py-0.5 text-xs font-medium ${cls}`}>{children}</span>;
}

export const DemoTag = ({ what = "Demo data" }: { what?: string }) => <Tag tone="demo">{what}</Tag>;

export function Card({ children, className = "", lift = false }: { children: ReactNode; className?: string; lift?: boolean }) {
  return <div className={`min-w-0 rounded-2xl border border-mist bg-white/80 p-5 shadow-lg shadow-black/20 backdrop-blur-sm ${lift ? "lift" : ""} ${className}`}>{children}</div>;
}

export function Loading({ what = "Loading" }: { what?: string }) {
  return <p className="text-ink-soft" role="status">{what}…</p>;
}

/** Friendly, recoverable error. `onRetry` re-runs the failed request; the user's data is never lost by a failed read. */
export function ErrorNote({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  return (
    <div role="alert" className="rounded-xl border border-alert/40 bg-red-50 px-4 py-3 text-sm">
      <p className="font-medium text-alert">Something went wrong. Your data has not been lost.</p>
      {(error as Error)?.message && <p className="mt-1 whitespace-pre-line text-ink-soft">{(error as Error).message}</p>}
      {onRetry && <button type="button" className="btn-quiet mt-2 px-3 py-1" onClick={onRetry}>Retry</button>}
    </div>
  );
}

/** Placeholder shown while a real request is in flight. */
export function Skeleton({ className = "h-24" }: { className?: string }) {
  return <div aria-hidden className={`animate-pulse rounded-2xl border border-mist bg-white/60 ${className}`} />;
}
export function PageSkeleton() {
  return <div role="status" aria-label="Loading" className="space-y-4"><Skeleton className="h-10 w-1/3" /><Skeleton className="h-32" /><div className="grid gap-4 md:grid-cols-3"><Skeleton /><Skeleton /><Skeleton /></div></div>;
}

export function EmptyState({ title, children, action }: { title: string; children?: ReactNode; action?: ReactNode }) {
  return (
    <div className="rounded-2xl border border-dashed border-mist px-5 py-9 text-center text-ink-soft">
      <b className="block text-base text-ink">{title}</b>
      {children && <p className="mt-1">{children}</p>}
      {action && <div className="mt-3">{action}</div>}
    </div>
  );
}

/** Segmented single-choice filter. Announces its state to assistive tech. */
export function Seg<T extends string>({ label, value, options, onChange }: { label: string; value: T; options: { value: T; label: string; count?: number }[]; onChange: (v: T) => void }) {
  return (
    <div role="group" aria-label={label} className="inline-flex flex-wrap overflow-hidden rounded-xl border border-mist">
      {options.map((o) => (
        <button key={o.value} type="button" aria-pressed={value === o.value} onClick={() => onChange(o.value)}
          className={`px-3 py-1.5 text-sm ${value === o.value ? "bg-brand font-semibold text-white" : "text-ink-soft hover:bg-route-tint"}`}>
          {o.label}{o.count !== undefined && <span className="ml-1 text-xs opacity-80">{o.count}</span>}
        </button>
      ))}
    </div>
  );
}

const STATE_STYLE: Record<string, string> = { acquired: "border-moss/50 bg-green-50 text-moss", in_progress: "border-signal/50 bg-signal/10 text-signal", missing: "border-alert/50 bg-red-50 text-alert" };
export const STATE_LABEL: Record<string, string> = { acquired: "Acquired", in_progress: "In progress", missing: "Missing" };
export function StatePill({ state }: { state: string }) {
  return <span className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${STATE_STYLE[state] ?? ""}`}>{STATE_LABEL[state] ?? state}</span>;
}

/** Shown when a module has nothing real to compute yet. Never fills the gap with sample numbers. */
export function NeedsSetup({ needs }: { needs: "target_role" | "assessment" | string | null | undefined }) {
  if (!needs) return null;
  const msg = needs === "target_role" ? "Choose a target role to see this." : "This needs your skills first. Complete the assessment or upload a resume.";
  return (
    <Card>
      <p className="text-ink-soft">{msg}</p>
      <Link to="/onboarding" className="btn mt-4">{needs === "target_role" ? "Choose a role" : "Assess my skills"}</Link>
    </Card>
  );
}

/** The WHAT / WHY / WHY NOW / IMPACT / NEXT block (spec §44). */
export function Explain({ r }: { r: Json }) {
  const rows: [string, string][] = [["What", r.what], ["Why", r.why], ["Why now", r.why_now], ["Impact", r.impact], ["Next", r.next]];
  return (
    <dl className="grid gap-x-6 gap-y-2 text-sm sm:grid-cols-[6rem_1fr]">
      {rows.map(([k, v]) => (
        <div key={k} className="contents">
          <dt className="font-medium text-ink-faint">{k}</dt>
          <dd>{v}</dd>
        </div>
      ))}
    </dl>
  );
}

export function LevelTag({ level }: { level: string }) {
  const label = level === "none" ? "Not started" : level[0].toUpperCase() + level.slice(1);
  return <Tag tone={level === "none" ? "plain" : level === "beginner" ? "warn" : "good"}>{label}</Tag>;
}
