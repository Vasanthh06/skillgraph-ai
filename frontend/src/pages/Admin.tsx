import { useEffect, useState } from "react";
import { http } from "../services/api";

type Row = {id: string; full_name: string; created_at: string; is_active: boolean; email_verified: boolean; target_role: string | null};
export default function Admin() {
  const [rows, setRows] = useState<Row[]>([]);
  const [offset, setOffset] = useState(0);
  const [query, setQuery] = useState("");
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    http.get<{users: Row[]}>(`/admin/users?offset=${offset}&q=${encodeURIComponent(query)}`).then(r => {if (active) {setRows(r.users); setError("");}}).catch(e => {if (active) {setRows([]); setError(e.message);}});
    return () => { active = false; };
  }, [offset, query]);
  return <section className="space-y-4"><h1 className="text-3xl font-bold">Account administration</h1><p>Read-only, server-authorized account overview. No credentials or reset tokens are exposed.</p>
    <label className="label">Search names<input className="field" value={query} maxLength={80} onChange={e => {setQuery(e.target.value); setOffset(0);}} /></label>
    {error && <p role="alert">{error}</p>}
    <div className="overflow-x-auto"><table className="w-full text-left text-sm"><thead><tr>{["Name", "Created", "Goal", "Email verified", "Active"].map(x => <th className="p-3" key={x}>{x}</th>)}</tr></thead><tbody>{rows.map(u => <tr className="border-t border-mist" key={u.id}><td className="p-3">{u.full_name}</td><td className="p-3">{u.created_at.slice(0,10)}</td><td className="p-3">{u.target_role ?? "Not selected"}</td><td className="p-3">{u.email_verified ? "Yes" : "No"}</td><td className="p-3">{u.is_active ? "Yes" : "No"}</td></tr>)}</tbody></table></div>
    <div className="flex gap-3"><button className="btn" disabled={!offset} onClick={() => setOffset(Math.max(0,offset-25))}>Previous</button><button className="btn" disabled={rows.length<25} onClick={() => setOffset(offset+25)}>Next</button></div>
  </section>;
}
