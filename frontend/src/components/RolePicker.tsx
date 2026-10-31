import { useState } from "react";
import { ErrorNote, Loading, Tag } from "./ui";
import SaveBar from "./SaveBar";
import { useAction, useGet } from "../hooks/useApi";
import { http } from "../services/api";
import { useDirtyFlag } from "../store/dirty";
import type { Json } from "../types/api";

/** Choose a target role. Selecting only highlights a card; the role changes when the user presses Save. */
export default function RolePicker({ onSaved }: { onSaved?: () => void }) {
  const [q, setQ] = useState("");
  const [custom, setCustom] = useState("");
  const [selected, setSelected] = useState<string | null>(null);
  const roles = useGet<Json[]>(`/roles?q=${encodeURIComponent(q)}`);
  const profile = useGet<Json>("/profile");
  const saved: string | null = profile.data?.target_role ?? null;
  const save = useAction((name: string) => http.put<Json>("/roles/target", { name }), "Target role saved. Your gap, roadmap, projects, jobs and interview prep have been recalculated.");

  const dirty = selected !== null && selected !== saved;
  useDirtyFlag("/role", "Target role", dirty);
  const pick = selected ?? saved;

  return (
    <div>
      <h2 className="text-xl font-bold">What role do you want to become?</h2>
      <p className="mt-1 text-sm text-ink-soft">Pick one, then press Save. Changing it recalculates everything for the new role and keeps the skills you've already shown.</p>
      {saved && <p className="mt-2 text-sm text-ink-soft">Saved target role: <b>{saved}</b></p>}
      <label className="label mt-4" htmlFor="rq">Search roles</label>
      <input id="rq" className="field" value={q} onChange={(e) => setQ(e.target.value)} placeholder="e.g. cloud, data, design" />
      {roles.isLoading && <Loading />}
      <ul className="mt-4 grid gap-3 sm:grid-cols-2">
        {roles.data?.map((r) => (
          <li key={r.name}>
            <button type="button" aria-pressed={pick === r.name} onClick={() => setSelected(r.name)}
              className={`h-full w-full rounded-lg border p-4 text-left hover:border-route ${pick === r.name ? "border-route bg-route-tint" : "border-mist bg-white"}`}>
              <span className="font-display text-lg font-bold">{r.name}</span>
              <span className="mt-1 block text-sm text-ink-soft">{r.description}</span>
              <span className="mt-2 flex flex-wrap gap-2 text-xs text-ink-faint">{r.skill_count} skills {r.limited_coverage && <Tag>Limited coverage</Tag>} {selected === r.name && selected !== saved && <Tag tone="demo">Selected, not saved</Tag>}</span>
            </button>
          </li>
        ))}
      </ul>
      <div className="mt-6">
        <label className="label" htmlFor="cr">Or enter a custom role</label>
        <div className="flex gap-2">
          <input id="cr" className="field" value={custom} onChange={(e) => setCustom(e.target.value)} />
          <button type="button" className="btn-quiet" disabled={!custom.trim()} onClick={() => setSelected(custom.trim())}>Select</button>
        </div>
        <p className="mt-1 text-xs text-ink-faint">Custom roles borrow requirements from the closest curated role and are marked as generated.</p>
      </div>
      <SaveBar count={dirty ? 1 : 0} saving={save.isPending} saveLabel="Save target role" onDiscard={() => setSelected(null)}
        onSave={() => selected && save.mutate(selected, { onSuccess: () => { setSelected(null); onSaved?.(); } })}
        error={(save.error as Error | null)?.message} />
      {save.error && <div className="mt-2"><ErrorNote error={save.error} /></div>}
    </div>
  );
}
