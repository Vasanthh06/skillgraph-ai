import { NavLink } from "react-router-dom";
import { useDirty } from "../store/dirty";

export const CAREER_TABS = [
  { to: "/profile", label: "Profile" },
  { to: "/role", label: "Target Role" },
  { to: "/assessment", label: "Assessment" },
] as const;

/** Profile, Target Role and Assessment are one hub; Resume Analysis has its own page. */
export default function CareerTabs() {
  const { entries } = useDirty();
  return (
    <nav aria-label="Profile sections" className="mb-6 flex w-fit max-w-full flex-wrap gap-1.5 rounded-2xl border border-mist bg-white/80 p-1.5">
      {CAREER_TABS.map((t) => (
        <NavLink key={t.to} to={t.to}
          className={({ isActive }) => `flex items-center gap-2 rounded-xl px-4 py-1.5 text-sm ${isActive ? "bg-brand font-semibold text-white shadow-glow" : "text-ink-soft hover:text-ink"}`}>
          {t.label}
          {entries[t.to] && <span aria-label="unsaved changes" title="Unsaved changes" className="inline-block h-2 w-2 rounded-full bg-signal shadow-[0_0_8px_#FBBF24]" />}
        </NavLink>
      ))}
    </nav>
  );
}
