"use client";

import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { call } from "@/lib/client";

interface Started {
  email: string;
  recovery_codes?: string[] | null;
}

interface Me {
  email: string;
  unused_recovery_codes: number;
}

type Mode = "signin" | "signup" | "forgot";
type Action = "codes" | "claim" | "logout-all" | "delete" | null;

const NOT_VERIFIED =
  "The email is only your user name: nothing is sent to it and nobody checks that it is yours.";

// Shows the eight recovery codes once, and does not let the person go on until they say they saved them.
export function RecoveryCodes({ codes, onDone }: { codes: string[]; onDone: () => void }) {
  const [saved, setSaved] = useState(false);
  const text = codes.join("\n");
  function download() {
    const url = URL.createObjectURL(new Blob([text + "\n"], { type: "text/plain" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = "graphlens-recovery-codes.txt";
    link.click();
    URL.revokeObjectURL(url);
  }
  return (
    <section className="card" aria-labelledby="codes-title">
      <h2 id="codes-title">Save your recovery codes</h2>
      <p>
        These 8 codes are the only way to reset your password without the owner. Each works once. They
        are shown <strong>only now</strong> and the server keeps just a scrambled form of them.
      </p>
      <ul className="codes">
        {codes.map((code) => (
          <li key={code}>
            <code>{code}</code>
          </li>
        ))}
      </ul>
      <div className="row-actions">
        <button type="button" onClick={() => void navigator.clipboard?.writeText(text)}>
          Copy
        </button>
        <button type="button" onClick={download}>
          Download as a file
        </button>
      </div>
      <label className="check">
        <input type="checkbox" checked={saved} onChange={(e) => setSaved(e.target.checked)} />I saved
        my recovery codes somewhere safe
      </label>
      <button type="button" className="primary" disabled={!saved} onClick={onDone}>
        Continue
      </button>
    </section>
  );
}

function Field({
  label,
  type,
  value,
  onChange,
  autoComplete,
}: {
  label: string;
  type: "email" | "password" | "text";
  value: string;
  onChange: (value: string) => void;
  autoComplete: string;
}) {
  return (
    <label className="field">
      <span>{label}</span>
      <input
        type={type}
        value={value}
        autoComplete={autoComplete}
        onChange={(e) => onChange(e.target.value)}
        required
      />
    </label>
  );
}

export default function AccountView() {
  const [me, setMe] = useState<Me | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [mode, setMode] = useState<Mode>("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [codes, setCodes] = useState<string[] | null>(null);
  const [action, setAction] = useState<Action>(null);
  const [confirmDelete, setConfirmDelete] = useState(false);

  useEffect(() => {
    void call<Me>("/api/auth/me").then((res) => {
      setMe(res.ok ? res.data : null);
      setLoaded(true);
    });
  }, []);

  function reload() {
    window.location.reload();
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setMessage("");
    const path = mode === "signup" ? "signup" : mode === "forgot" ? "reset" : "login";
    const body =
      mode === "forgot"
        ? { email, recovery_code: code, new_password: password }
        : { email, password };
    const res = await call<Started>(`/api/auth/${path}`, "POST", body);
    setBusy(false);
    setPassword("");
    setCode("");
    if (!res.ok) {
      setMessage(res.message);
    } else if (res.data?.recovery_codes) {
      setCodes(res.data.recovery_codes); // shown once, before anything else
    } else {
      reload();
    }
  }

  async function withPassword(path: string, method: "POST" | "DELETE") {
    setBusy(true);
    setMessage("");
    const res = await call<{ recovery_codes?: string[]; detail?: Record<string, number> }>(
      `/api/auth/${path}`,
      method,
      { password },
    );
    setBusy(false);
    setPassword("");
    if (!res.ok) {
      setMessage(res.message);
      return;
    }
    setAction(null);
    setConfirmDelete(false);
    if (path === "recovery-codes" && res.data?.recovery_codes) setCodes(res.data.recovery_codes);
    else if (path === "claim") {
      const n = res.data?.detail?.conversations ?? 0;
      setMessage(`Done. ${n} earlier question${n === 1 ? "" : "s"} moved into your account.`);
      setTimeout(reload, 1500);
    } else reload();
  }

  async function signOut() {
    await call("/api/auth/logout", "POST");
    reload();
  }

  if (codes) {
    return <RecoveryCodes codes={codes} onDone={reload} />;
  }
  if (!loaded) return <p className="muted">Loading…</p>;

  if (me) {
    return (
      <section className="card" aria-labelledby="account-title">
        <h2 id="account-title">Account</h2>
        <p>
          Signed in as <strong>{me.email}</strong>. Your questions, saved answers and settings follow
          you to any browser where you sign in.
        </p>
        <p className="muted">
          Unused recovery codes: {me.unused_recovery_codes} of 8. {NOT_VERIFIED}
        </p>
        <div className="row-actions">
          <button type="button" onClick={signOut}>
            Sign out
          </button>
          <button type="button" onClick={() => setAction("codes")}>
            New recovery codes
          </button>
          <button type="button" onClick={() => setAction("claim")}>
            Move this browser’s earlier questions here
          </button>
          <button type="button" onClick={() => setAction("logout-all")}>
            Sign out everywhere
          </button>
          <button type="button" className="danger" onClick={() => setAction("delete")}>
            Delete my account
          </button>
        </div>
        {action && (
          <form
            className="fields"
            onSubmit={(e) => {
              e.preventDefault();
              if (action === "delete" && !confirmDelete) {
                setConfirmDelete(true);
                return;
              }
              const path =
                action === "codes"
                  ? "recovery-codes"
                  : action === "delete"
                    ? "account"
                    : action;
              void withPassword(path, action === "delete" ? "DELETE" : "POST");
            }}
          >
            <p className="muted">
              {action === "codes" && "A new set replaces the old codes; the old ones stop working."}
              {action === "claim" &&
                "Works once. It moves what you asked before signing in, in this browser, into this account."}
              {action === "logout-all" && "Ends every session of this account, including this one."}
              {action === "delete" &&
                "This removes the account and all its questions, saved answers and ratings. It cannot be undone."}
            </p>
            <Field
              label="Your password, to confirm"
              type="password"
              value={password}
              onChange={setPassword}
              autoComplete="current-password"
            />
            <div className="row-actions">
              <button type="submit" className={action === "delete" ? "danger" : "primary"} disabled={busy}>
                {action === "delete" && confirmDelete ? "Yes, delete everything" : "Confirm"}
              </button>
              <button
                type="button"
                onClick={() => {
                  setAction(null);
                  setConfirmDelete(false);
                  setPassword("");
                }}
              >
                Cancel
              </button>
            </div>
          </form>
        )}
        <p role="status" className="muted">
          {message}
        </p>
      </section>
    );
  }

  return (
    <section className="card" aria-labelledby="account-title">
      <h2 id="account-title">
        {mode === "signup" ? "Create an account" : mode === "forgot" ? "Reset your password" : "Sign in"}
      </h2>
      <p className="muted">
        An account is optional. Without one you stay an anonymous visitor tied to this browser. {NOT_VERIFIED}
      </p>
      <form className="fields" onSubmit={submit}>
        <Field label="Email" type="email" value={email} onChange={setEmail} autoComplete="username" />
        {mode === "forgot" && (
          <Field
            label="One recovery code"
            type="text"
            value={code}
            onChange={setCode}
            autoComplete="off"
          />
        )}
        <Field
          label={mode === "forgot" ? "New password (at least 10 characters)" : "Password"}
          type="password"
          value={password}
          onChange={setPassword}
          autoComplete={mode === "signin" ? "current-password" : "new-password"}
        />
        {mode === "signup" && (
          <p className="muted">
            At least 10 characters. You will get 8 recovery codes next: without them, a lost password
            can only be reset by the person who runs this installation.
          </p>
        )}
        <div className="row-actions">
          <button type="submit" className="primary" disabled={busy}>
            {mode === "signup" ? "Create account" : mode === "forgot" ? "Reset password" : "Sign in"}
          </button>
        </div>
      </form>
      <div className="row-actions">
        {mode !== "signin" && (
          <button type="button" onClick={() => setMode("signin")}>
            I have an account
          </button>
        )}
        {mode !== "signup" && (
          <button type="button" onClick={() => setMode("signup")}>
            Create an account
          </button>
        )}
        {mode !== "forgot" && (
          <button type="button" onClick={() => setMode("forgot")}>
            Forgot my password
          </button>
        )}
      </div>
      <p role="status" className="muted">
        {message}
      </p>
    </section>
  );
}
