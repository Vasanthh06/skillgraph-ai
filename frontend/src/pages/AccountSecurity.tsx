import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import AuthLayout from "../layouts/AuthLayout";
import { http } from "../services/api";

export default function AccountSecurity() {
  const path = useLocation().pathname;
  const mode = path.endsWith("reset") ? "reset" : path.endsWith("verify") ? "verify" : "forgot";
  const [token] = useState(() => new URLSearchParams(location.hash.slice(1)).get("token") ?? "");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => { history.replaceState(null, "", location.pathname); }, []);
  async function submit() {
    if (busy) return;
    setBusy(true);
    try {
      const result = await http.post<{message: string}>(`/auth/${mode === "forgot" ? "forgot-password" : mode === "reset" ? "reset-password" : "verify-email"}`, mode === "forgot" ? {email} : mode === "reset" ? {token, password} : {token});
      setMessage(result.message);
    } catch (e) { setMessage((e as Error).message); }
    finally { setBusy(false); }
  }
  return <AuthLayout title={mode === "forgot" ? "Recover your account" : mode === "reset" ? "Choose a new password" : "Verify your email"} subtitle="Secure, single-use account links expire after 20 minutes.">
    <form className="space-y-4" onSubmit={e => {e.preventDefault(); void submit();}}>
      {mode === "forgot" && <label className="label">Registered email<input className="field" type="email" autoComplete="email" value={email} onChange={e => setEmail(e.target.value)} required /></label>}
      {mode === "reset" && <label className="label">New password<input className="field" type="password" minLength={15} maxLength={128} autoComplete="new-password" value={password} onChange={e => setPassword(e.target.value)} required /><span className="text-sm">15–128 characters; passphrases welcome.</span></label>}
      <button className="btn w-full" disabled={busy}>{busy ? "Working…" : mode === "forgot" ? "Send recovery email" : "Confirm"}</button>
      <p role="status" aria-live="polite">{message}</p>
      <Link to="/login" className="underline">Return to sign in</Link>
    </form>
  </AuthLayout>;
}
