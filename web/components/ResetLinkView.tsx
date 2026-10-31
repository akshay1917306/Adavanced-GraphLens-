"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { call } from "@/lib/client";

// The reset link carries its one-time token after "#", which browsers never send to a server or in
// a Referer header. It is read once here, kept only in memory, and removed from the address bar.
export default function ResetLinkView() {
  const [token, setToken] = useState<string | null>(null);
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);

  useEffect(() => {
    const match = /(?:^#|&)token=([A-Za-z0-9_-]{20,100})/.exec(window.location.hash);
    const found = match ? match[1] : "";
    if (match) window.history.replaceState(null, "", window.location.pathname);
    queueMicrotask(() => setToken(found));
  }, []);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    const res = await call("/api/auth/reset-with-link", "POST", { token, new_password: password });
    setBusy(false);
    setPassword("");
    if (res.ok) setDone(true);
    else setMessage(res.message);
  }

  if (token === null) return <p className="muted">Loading…</p>;

  return (
    <div className="shell">
      <header className="top">
        <h1>GraphLens</h1>
      </header>
      <section className="card" aria-labelledby="reset-title">
        <h2 id="reset-title">Choose a new password</h2>
        {done ? (
          <>
            <p>Your password was changed and every older session was ended. You are signed in.</p>
            <p className="muted">
              Your old recovery codes still work. If you lost them, make a new set on the Account page.
            </p>
            <Link href="/">Go to GraphLens</Link>
          </>
        ) : token === "" ? (
          <p>
            This page needs the full link the owner gave you. A link works once and only for 30
            minutes. Ask the owner for a new one.
          </p>
        ) : (
          <form className="fields" onSubmit={submit}>
            <label className="field">
              <span>New password (at least 10 characters)</span>
              <input
                type="password"
                value={password}
                autoComplete="new-password"
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </label>
            <div className="row-actions">
              <button type="submit" className="primary" disabled={busy}>
                Change password
              </button>
            </div>
            <p role="status" className="muted">
              {message}
            </p>
          </form>
        )}
      </section>
    </div>
  );
}
