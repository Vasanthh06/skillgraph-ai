import { Link } from "react-router-dom";
import { useTheme } from "../store/theme";

export default function ThemeToggle() {
  const {preference, setPreference} = useTheme();
  return <div role="group" aria-label="Color theme" className="theme-switch">
    {([{id:"light", icon:"☀", label:"Light"}, {id:"dark", icon:"☾", label:"Dark"}, {id:"system", icon:"◐", label:"System"}] as const).map(p =>
      <button type="button" key={p.id} title={`${p.label} theme`} aria-label={`${p.label} theme`} aria-pressed={preference === p.id} onClick={() => setPreference(p.id)}>
        <span aria-hidden="true">{p.icon}</span><span className="hidden sm:inline">{p.label}</span>
      </button>)}
  </div>;
}
export function ThemeBar() {
  return <div className="theme-bar"><div className="theme-bar-inner">
    <Link to="/" className="inline-flex items-center gap-2 text-xs font-semibold"><span className="brand-glyph" aria-hidden="true">S</span><span>SkillGraph <span className="text-route">AI</span></span></Link>
    <div className="flex items-center gap-3"><span className="hidden text-xs text-ink-faint md:inline">Your space. Your perspective.</span><ThemeToggle /></div>
  </div></div>;
}
