import { useId } from "react";
import { Link } from "react-router-dom";
import { useCountUp } from "../hooks/useMotion";
import { Card } from "./ui";
import type { Json } from "../types/api";

/** Circular readiness gauge. The arc and the number are driven by the same eased value, and the final value is exactly `value`. */
export function ProgressRing({ value, size = 176, label = "Career readiness" }: { value: number; size?: number; label?: string }) {
  const id = useId().replace(/:/g, "");
  const R = 64;
  const C = 2 * Math.PI * R;
  const v = Math.max(0, Math.min(100, value));
  const shown = useCountUp(v);
  return (
    <div role="img" aria-label={`${label} ${v}%`} className="relative" style={{ width: size, height: size }}>
      <svg viewBox="0 0 160 160" aria-hidden className="h-full w-full -rotate-90 drop-shadow-[0_0_8px_rgba(124,92,255,0.55)]">
        <defs>
          <linearGradient id={id} x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stopColor="#35E0D2" /><stop offset=".5" stopColor="#3B82FF" /><stop offset="1" stopColor="#B35CFF" />
          </linearGradient>
        </defs>
        <circle cx="80" cy="80" r={R} fill="none" stroke="rgba(132,150,255,.18)" strokeWidth="12" />
        <circle cx="80" cy="80" r={R} fill="none" stroke={`url(#${id})`} strokeWidth="12" strokeLinecap="round" strokeDasharray={C} strokeDashoffset={C * (1 - shown / 100)} />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <b className="font-display text-5xl leading-none">{shown}%</b>
        <small className="mt-1 text-xs uppercase tracking-wider text-ink-faint">readiness</small>
      </div>
    </div>
  );
}

/** A number that eases to its real value (and snaps to it for reduced-motion users). */
export function AnimatedNumber({ value, suffix = "" }: { value: number; suffix?: string }) {
  const shown = useCountUp(value);
  return <>{shown}{suffix}</>;
}

/** The single most useful next step, with the reason it was chosen. Comes from the backend (rules over the user's own evidence). */
export function NextBestActionCard({ action }: { action: Json }) {
  return (
    <div className="relative mt-5 rounded-2xl border border-mist bg-gradient-to-br from-glow-blue/20 to-glow-violet/25 p-5 shadow-glow">
      <p className="text-xs font-semibold uppercase tracking-widest text-glow-cyan">✦ Next best action</p>
      <h2 className="mt-1 text-2xl font-bold">{action.title}</h2>
      <p className="mb-4 mt-2 max-w-xl text-ink-soft">{action.reason}</p>
      <Link to={action.route} className="btn">Do this now →</Link>
    </div>
  );
}

/** "What is preventing you reaching 80%?" Gains are simulated by the backend: readiness is re-run as if each fix were done. */
export function BlockersCard({ data }: { data: Json }) {
  return (
    <Card>
      <h3 className="text-base font-bold">What's preventing you from reaching {data.goal}%?</h3>
      <p className="mt-1 text-sm text-ink-soft">
        You're at <b>{data.current}%</b>{data.reached ? ". You're above your goal." : `, ${data.to_go} points to go.`} Each fix shows how many points it would add.
      </p>
      {data.blockers.length === 0 ? <p className="mt-3 text-sm text-ink-faint">Nothing is holding you back right now.</p> : (
        <ul className="mt-3 divide-y divide-mist">
          {data.blockers.map((b: Json) => (
            <li key={`${b.kind}-${b.label}`} className="flex items-center justify-between gap-3 py-2 text-sm">
              <span>{b.label}</span>
              <span className="flex items-center gap-3 whitespace-nowrap">
                {b.gain === null ? <span className="text-xs text-ink-faint">not measured</span> : <span className="font-display font-bold text-glow-cyan">+{b.gain}</span>}
                <Link to={b.route} className="text-route underline">Do it</Link>
              </span>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

/** Progress through the career loop, from the backend's stored-evidence `journey`. */
export function JourneyStrip({ steps }: { steps: Json[] }) {
  return (
    <ol aria-label="Your career journey" className="mt-5 grid grid-cols-2 gap-2 md:grid-cols-6">
      {steps.map((s) => (
        <li key={s.label} className={`relative rounded-xl border bg-white/80 px-3 py-2 text-xs ${s.done ? "border-moss/50" : s.next ? "border-glow-violet shadow-glow" : "border-mist"}`}>
          <b className="block text-sm text-ink">{s.label}</b>
          <span className="text-ink-soft">{s.done ? "Done" : s.next ? "Up next" : "Later"}</span>
          {s.done && <span aria-hidden className="absolute right-2 top-1.5 font-bold text-moss">✓</span>}
        </li>
      ))}
    </ol>
  );
}
