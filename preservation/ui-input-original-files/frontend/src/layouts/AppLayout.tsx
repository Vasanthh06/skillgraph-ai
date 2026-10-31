import { useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import Avatar from "../components/Avatar";
import Icon, { type IconName } from "../components/Icon";
import { useProfile } from "../hooks/useProfile";
import { useAuth } from "../store/auth";
import { useDirty } from "../store/dirty";
import { useNotice } from "../store/notice";

interface Stop { to: string; label: string; icon: IconName; hub?: boolean }

// The seven primary destinations. Profile is a hub (Profile, Target Role, Assessment); the existing tools stay under "More tools".
const MAIN: Stop[] = [
  { to: "/dashboard", label: "Dashboard", icon: "dash" },
  { to: "/resume", label: "Resume Analysis", icon: "file" },
  { to: "/skill-graph", label: "Skill Graph", icon: "net" },
  { to: "/roadmap", label: "Learning Roadmap", icon: "route" },
  { to: "/jobs", label: "Job Matching", icon: "brief" },
  { to: "/projects", label: "Project Recommendations", icon: "rocket" },
  { to: "/profile", label: "Profile", icon: "user", hub: true },
];
const MORE: Stop[] = [
  { to: "/skill-gap", label: "Skill Gap", icon: "target" },
  { to: "/learn", label: "Learn & Build", icon: "book" },
  { to: "/interview", label: "Interview Prep", icon: "chat" },
  { to: "/explore", label: "Skill Explorer", icon: "compass" },
];
const HUB_PATHS = ["/profile", "/role", "/assessment", "/onboarding"];
const LABELS: Record<string, string> = Object.fromEntries([...MAIN, ...MORE].map((s) => [s.to, s.label]).concat([["/role", "Target Role"], ["/assessment", "Assessment"], ["/onboarding", "Onboarding"]]));

export default function AppLayout() {
  const { user, signOut } = useAuth();
  const { data: profile } = useProfile();
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const { message, clear } = useNotice();
  const { entries } = useDirty();
  const dirtyLabels = [...new Set(Object.values(entries))];
  const [leaving, setLeaving] = useState<string | null>(null);
  const [collapsed, setCollapsed] = useState(false);   // a view preference only; kept in memory, not stored
  // Sidebar navigation never silently discards unsaved edits: ask first.
  const guard = (e: React.MouseEvent, to: string) => { if (dirtyLabels.length) { e.preventDefault(); setLeaving(to); } };
  const hubDirty = Object.keys(entries).some((k) => HUB_PATHS.includes(k));
  const page = LABELS[pathname] ?? "SkillGraph";

  const item = (s: Stop) => {
    const active = s.hub ? HUB_PATHS.includes(pathname) : pathname === s.to || pathname.startsWith(`${s.to}/`);
    const dirty = s.hub ? hubDirty : !!entries[s.to];
    return (
      <li key={s.to} className="shrink-0">
        <NavLink to={s.to} onClick={(e) => guard(e, s.to)} title={s.label} aria-current={active ? "page" : undefined}
          className={`relative flex items-center gap-3 whitespace-nowrap rounded-xl border px-3 py-2 text-sm ${collapsed ? "md:justify-center md:px-0" : ""} ${
            active ? "border-mist bg-gradient-to-br from-glow-blue/30 to-glow-violet/30 font-semibold text-white" : "border-transparent text-ink-soft hover:bg-route-tint hover:text-ink"
          }`}>
          <Icon name={s.icon} className="hidden h-[18px] w-[18px] md:block" />
          <span className={collapsed ? "md:sr-only" : ""}>{s.label}</span>
          {dirty && <span aria-label="unsaved changes" title="Unsaved changes" className={`inline-block h-2 w-2 rounded-full bg-signal shadow-[0_0_8px_#FBBF24] ${collapsed ? "md:absolute md:right-3 md:top-2" : "ml-auto"}`} />}
        </NavLink>
      </li>
    );
  };

  return (
    <div className={`min-h-screen md:grid ${collapsed ? "md:grid-cols-[4.75rem_minmax(0,1fr)]" : "md:grid-cols-[15.5rem_minmax(0,1fr)]"} transition-[grid-template-columns] duration-300`}>
      <aside className="flex flex-col border-b border-mist bg-[#080D24]/90 backdrop-blur md:sticky md:top-0 md:h-screen md:border-b-0 md:border-r">
        <div className={`flex items-center justify-between gap-3 px-5 py-4 md:py-5 ${collapsed ? "md:justify-center md:px-0" : ""}`}>
          <span className="flex items-center gap-2.5">
            <img src="/logo-mark.png" alt="" className="h-10 w-10 drop-shadow-[0_0_8px_rgba(124,92,255,0.5)]" />
            <span className={`font-display text-xl font-bold ${collapsed ? "md:hidden" : ""}`}>SkillGraph <span className="gradient-text">AI</span></span>
          </span>
          <span className="text-xs text-ink-faint md:hidden">{user?.full_name}</span>
        </div>

        <nav aria-label="Main" className="overflow-x-auto px-3 pb-3 md:flex-1 md:overflow-y-auto md:pb-0">
          <ol className="flex gap-1 md:block md:space-y-1">{MAIN.map(item)}</ol>
          <p className={`hidden px-3 pb-1 pt-5 text-[11px] uppercase tracking-widest text-ink-faint ${collapsed ? "" : "md:block"}`}>More tools</p>
          <ol className="flex gap-1 md:mt-1 md:block md:space-y-1">{MORE.map(item)}</ol>
        </nav>

        <button type="button" onClick={() => setCollapsed(!collapsed)} aria-pressed={collapsed} aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"} title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          className="mx-auto my-3 hidden h-9 w-9 items-center justify-center rounded-xl border border-mist hover:bg-route-tint md:flex">
          <Icon name="chev" className={`h-[18px] w-[18px] transition-transform ${collapsed ? "rotate-180" : ""}`} />
        </button>

        <div className={`hidden border-t border-mist p-4 md:block ${collapsed ? "md:px-0" : ""}`}>
          <div className={`flex items-center gap-3 ${collapsed ? "justify-center" : ""}`}>
            <Avatar name={user?.full_name ?? "?"} src={profile?.photo_url} size={38} />
            <div className={`min-w-0 ${collapsed ? "hidden" : ""}`}>
              <p className="truncate text-sm font-semibold">{user?.full_name}</p>
              <p className="truncate text-xs text-ink-faint">{profile?.target_role ?? "No target role yet"}</p>
              <button className="text-xs text-ink-faint underline hover:text-ink" onClick={async () => { await signOut(); navigate("/login"); }}>Log out</button>
            </div>
          </div>
        </div>
      </aside>

      <main className="min-w-0 px-5 py-6 md:px-10 md:py-8">
        <div className="mb-5 flex items-center gap-3 text-sm text-ink-soft">
          <span>SkillGraph / <b className="text-ink">{page}</b></span><span className="flex-1" />
          {profile?.target_role && <span className="hidden rounded-full border border-mist bg-white/80 px-3 py-0.5 text-xs sm:inline">Target: {profile.target_role}</span>}
        </div>
        {message && (
          <p role="status" className="mb-6 flex items-center justify-between rounded-xl border border-moss/40 bg-green-50 px-4 py-2 text-sm font-medium text-moss">
            <span>✓ {message}</span>
            <button type="button" className="text-xs underline" onClick={clear}>Dismiss</button>
          </p>
        )}
        {leaving && (
          <div role="alertdialog" aria-label="Unsaved changes" className="mb-6 rounded-xl border border-l-4 border-signal bg-white px-4 py-3 text-sm">
            <p><b>You have unsaved changes</b> in {dirtyLabels.join(", ")}. If you leave now they will be lost.</p>
            <div className="mt-2 flex gap-2">
              <button type="button" className="btn-quiet px-3 py-1" onClick={() => setLeaving(null)}>Stay and save</button>
              <button type="button" className="btn-quiet px-3 py-1" onClick={() => { const to = leaving; setLeaving(null); navigate(to); }}>Leave without saving</button>
            </div>
          </div>
        )}
        {/* keyed by path: the entrance plays when the page changes, not when data inside it changes */}
        <div key={pathname} className="page-enter"><Outlet /></div>
        <div className="mt-10 md:hidden">
          <button className="btn-quiet" onClick={async () => { await signOut(); navigate("/login"); }}>Log out</button>
        </div>
      </main>
    </div>
  );
}
