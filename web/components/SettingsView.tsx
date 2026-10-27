"use client";

import { useState } from "react";
import { call } from "@/lib/client";
import { writeTheme } from "@/lib/theme";
import type { DeletedCounts, Preferences, ThemeChoice } from "@/lib/types";

interface Props {
  prefs: Preferences;
  onChange: (prefs: Preferences) => void;
}

const THEMES: ThemeChoice[] = ["system", "light", "dark"];

export default function SettingsView({ prefs, onChange }: Props) {
  const [message, setMessage] = useState("");
  const [confirming, setConfirming] = useState(false);

  async function update(next: Preferences) {
    onChange(next);
    writeTheme(next.theme);
    const res = await call<Preferences>("/api/preferences", "PUT", next);
    setMessage(res.ok ? "Saved." : res.message);
  }

  async function deleteAll() {
    const res = await call<DeletedCounts>("/api/me", "DELETE");
    setConfirming(false);
    if (res.ok && res.data) {
      setMessage(
        `Deleted ${res.data.conversations} questions, ${res.data.saved_answers} saved answers and ` +
          `${res.data.ratings} ratings. A new anonymous visit starts with your next question.`,
      );
    } else {
      setMessage(res.message);
    }
  }

  return (
    <section className="card" aria-labelledby="settings-title">
      <h2 id="settings-title">Settings</h2>

      <fieldset className="fields">
        <legend>Theme</legend>
        {THEMES.map((theme) => (
          <label key={theme} className="check">
            <input
              type="radio"
              name="theme"
              checked={prefs.theme === theme}
              onChange={() => update({ ...prefs, theme })}
            />
            {theme}
          </label>
        ))}
      </fieldset>

      <label className="check">
        <input
          type="checkbox"
          checked={prefs.evidence_panel_open}
          onChange={(e) => update({ ...prefs, evidence_panel_open: e.target.checked })}
        />
        Show “Why this answer” open by default
      </label>

      <h3>My data</h3>
      <p className="muted">
        You are an anonymous visitor: there is no account. Your history, saved answers, ratings and
        settings are linked only to a cookie in this browser.
      </p>
      {confirming ? (
        <div className="row-actions">
          <span>This removes everything stored for you and cannot be undone.</span>
          <button type="button" className="danger" onClick={deleteAll}>
            Yes, delete everything
          </button>
          <button type="button" onClick={() => setConfirming(false)}>
            Cancel
          </button>
        </div>
      ) : (
        <button type="button" onClick={() => setConfirming(true)}>
          Delete all my data
        </button>
      )}
      <p role="status" className="muted">
        {message}
      </p>
    </section>
  );
}
