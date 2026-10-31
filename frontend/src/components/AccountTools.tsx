import { useEffect, useState } from "react";
import { http } from "../services/api";

export default function AccountTools() {
  const [status, setStatus] = useState<{email_verified: boolean; is_admin: boolean; email_configured: boolean} | null>(null);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [requestId] = useState(() => crypto.randomUUID());
  useEffect(() => { http.get<typeof status>("/account/status").then(setStatus).catch(() => {}); }, []);
  async function action(path: string) {
    if (busy) return;
    setBusy(true);
    try { await http.post(path, path.includes("roadmap") ? {request_id: requestId} : undefined); setMessage("Request accepted. Check your inbox if email delivery is configured."); }
    catch (e) { setMessage((e as Error).message); }
    finally { setBusy(false); }
  }
  return <section className="my-4 rounded-2xl border border-mist bg-white p-4" aria-label="Account and delivery">
    <div className="flex flex-wrap items-center gap-3">
      <span className="text-sm">Email: {status?.email_verified ? "verified" : "not verified"}</span>
      {!status?.email_verified && <button className="btn" disabled={busy} onClick={() => void action("/auth/request-verification")}>Send verification email</button>}
      <button className="btn" disabled={busy || !status?.email_verified} onClick={() => void action("/roadmap/email")}>Email My Roadmap</button>
      {status?.is_admin && <a href="/admin" className="underline">Administration</a>}
    </div>
    {status && !status.email_configured && <p className="mt-2 text-sm">Email delivery requires operator configuration. No email has been sent.</p>}
    <p role="status" className="mt-2 text-sm">{message}</p>
  </section>;
}
