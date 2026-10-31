import { createContext, useContext, useLayoutEffect, useState, type ReactNode } from "react";
import { useLocation, useNavigate, useNavigationType } from "react-router-dom";

type Entry = {key: string; path: string};
type Trail = Record<number, Entry>;
const KEY = "sg_navigation";
const Context = createContext<{back: () => void; forward: () => void; canBack: boolean; canForward: boolean; fallback: boolean} | null>(null);

/** Observe router-created entries only. Never infer safe history from history.length,
 * never push sentinel entries, never navigate to a URL supplied from storage. */
export function NavigationProvider({children}: {children: ReactNode}) {
  const location = useLocation();
  const action = useNavigationType();
  const navigate = useNavigate();
  const [trail, setTrail] = useState<Trail>(() => {
    try {
      const parsed = JSON.parse(sessionStorage.getItem(KEY) ?? "{}");
      if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) return {};
      return Object.fromEntries(Object.entries(parsed).filter(([index, entry]) => {
        const item = entry as Entry | null;
        return /^\d+$/.test(index) && item && typeof item.key === "string" && typeof item.path === "string" && item.path.startsWith("/") && !item.path.startsWith("//");
      })) as Trail;
    } catch { return {}; }
  });
  const index: number = typeof history.state?.idx === "number" ? history.state.idx : 0;
  const path = location.pathname + location.search;
  useLayoutEffect(() => {
    setTrail(previous => {
      const next = {...previous};
      if (action === "PUSH") Object.keys(next).forEach(k => {if (+k >= index) delete next[+k];});
      // A new document entry with an unknown key indicates a different history chain.
      if (next[index] && next[index].key !== location.key && action === "POP") {
        Object.keys(next).forEach(k => delete next[+k]);
      }
      next[index] = {key: location.key, path};
      try { sessionStorage.setItem(KEY, JSON.stringify(next)); } catch { /* tab-memory fallback */ }
      return next;
    });
  }, [location.key, index, path, action]);
  const here = trail[index]?.key === location.key;
  const canBack = !!(here && trail[index-1]);
  const canForward = !!(here && trail[index+1]);
  const fallback = !canBack && location.pathname !== "/dashboard";
  return <Context.Provider value={{canBack, canForward, fallback,
    back: () => { if (canBack) navigate(-1); else if (fallback) navigate("/dashboard", {replace:true}); },
    forward: () => {if (canForward) navigate(1);},
  }}>{children}</Context.Provider>;
}
export function useNavigation() {
  const value = useContext(Context);
  if (!value) throw new Error("NavigationProvider required");
  return value;
}
