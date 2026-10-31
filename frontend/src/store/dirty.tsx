import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

interface DirtyState { entries: Record<string, string>; set: (key: string, label: string | null) => void }
const Ctx = createContext<DirtyState | null>(null);

/** Tracks which pages currently hold unsaved edits, so navigation can warn instead of silently losing them. */
export function DirtyProvider({ children }: { children: ReactNode }) {
  const [entries, setEntries] = useState<Record<string, string>>({});
  const set = useCallback((key: string, label: string | null) => {
    setEntries((prev) => {
      if (label === null) {
        if (!(key in prev)) return prev;
        const { [key]: _drop, ...rest } = prev;
        return rest;
      }
      return prev[key] === label ? prev : { ...prev, [key]: label };
    });
  }, []);
  const value = useMemo(() => ({ entries, set }), [entries, set]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useDirty(): DirtyState {
  const c = useContext(Ctx);
  if (!c) throw new Error("useDirty must be used inside DirtyProvider");
  return c;
}

/** Register a form's unsaved state. Also warns on tab close / reload while dirty. */
export function useDirtyFlag(key: string, label: string, dirty: boolean) {
  const { set } = useDirty();
  useEffect(() => {
    set(key, dirty ? label : null);
    return () => set(key, null);
  }, [key, label, dirty, set]);
  useEffect(() => {
    if (!dirty) return;
    const warn = (e: BeforeUnloadEvent) => { e.preventDefault(); e.returnValue = ""; };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [dirty]);
}
