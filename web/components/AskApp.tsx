"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import { askStream, call } from "@/lib/client";
import { writeTheme } from "@/lib/theme";
import type { AskResponse, Preferences } from "@/lib/types";
import AnswerCard from "./AnswerCard";
import EvidencePanel from "./EvidencePanel";
import HistoryView from "./HistoryView";
import SavedView from "./SavedView";
import AccountView from "./AccountView";
import SettingsView from "./SettingsView";
import ThemeToggle from "./ThemeToggle";

const MAX_CHARS = 4000;

type View = "ask" | "history" | "saved" | "settings" | "account";

const VIEWS: { id: View; label: string }[] = [
  { id: "ask", label: "Ask" },
  { id: "history", label: "My questions" },
  { id: "saved", label: "Saved" },
  { id: "settings", label: "Settings" },
  { id: "account", label: "Account" },
];

const DEFAULT_PREFS: Preferences = { theme: "system", default_mode: "auto", evidence_panel_open: true };

export default function AskApp() {
  const [view, setView] = useState<View>("ask");
  const [question, setQuestion] = useState("");
  const [compare, setCompare] = useState(false);
  const [examples, setExamples] = useState<string[]>([]);
  const [live, setLive] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<AskResponse | null>(null);
  const [draft, setDraft] = useState("");
  const [selected, setSelected] = useState<string | null>(null);
  const [prefs, setPrefs] = useState<Preferences>(DEFAULT_PREFS);
  const resultRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    void (async () => {
      const list = await call<{ questions: string[]; live?: boolean }>("/api/examples");
      setExamples(list.data?.questions ?? []);
      setLive(list.data?.live === true);
      const saved = await call<Preferences>("/api/preferences");
      if (saved.ok && saved.data) {
        setPrefs(saved.data);
        if (saved.data.theme !== "system") writeTheme(saved.data.theme);
      }
    })();
  }, []);

  async function ask(text: string) {
    const trimmed = text.trim();
    if (!trimmed || busy) return;
    setBusy(true);
    setError("");
    setSelected(null);
    setDraft("");
    const res = await askStream<AskResponse>({ question: trimmed, compare }, (piece) =>
      setDraft((text) => text + piece),
    );
    setDraft("");
    if (res.ok && res.data) {
      setResult(res.data);
      setTimeout(() => resultRef.current?.focus(), 0);
    } else {
      setResult(null);
      setError(res.message);
    }
    setBusy(false);
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    void ask(question);
  }

  function askAgain(text: string) {
    setView("ask");
    setQuestion(text);
    void ask(text);
  }

  function pickLabel(label: string) {
    setSelected(label);
    document.getElementById(`source-${label}`)?.scrollIntoView({ block: "nearest" });
  }

  return (
    <div className="shell">
      <header className="top">
        <h1>GraphLens</h1>
        <ThemeToggle />
      </header>

      <nav className="nav" aria-label="Sections">
        {VIEWS.map((v) => (
          <button
            key={v.id}
            type="button"
            aria-current={view === v.id ? "page" : undefined}
            onClick={() => setView(v.id)}
          >
            {v.label}
          </button>
        ))}
      </nav>

      {view === "history" && <HistoryView onAskAgain={askAgain} />}
      {view === "saved" && <SavedView />}
      {view === "settings" && <SettingsView prefs={prefs} onChange={setPrefs} />}
      {view === "account" && <AccountView />}

      {view === "ask" && (
        <>
          <form onSubmit={submit} className="ask">
            <label htmlFor="question">Ask a question about the papers</label>
            <textarea
              id="question"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              maxLength={MAX_CHARS}
              rows={3}
              placeholder={
                examples.length > 0 && !live
                  ? "Choose one of the saved examples below (only these have full answers for now)"
                  : "Ask a question about the papers"
              }
            />
            <div className="ask-row">
              <label className="check">
                <input type="checkbox" checked={compare} onChange={(e) => setCompare(e.target.checked)} />
                Compare with normal RAG
              </label>
              <button type="submit" className="primary" disabled={busy || question.trim() === ""}>
                {busy ? "Working…" : "Ask"}
              </button>
            </div>
            {examples.length > 0 && (
              <div className="examples">
                <span className="muted">{live ? "Try an example:" : "Saved examples:"}</span>
                <ul>
                  {examples.map((q) => (
                    <li key={q}>
                      <button
                        type="button"
                        className="example"
                        onClick={() => {
                          setQuestion(q);
                          void ask(q);
                        }}
                      >
                        {q}
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </form>

          <div aria-live="polite" className="status-line">
            {busy ? (draft ? "Writing the answer, then checking its sources…" : "Looking for an answer…") : ""}
          </div>
          {busy && draft && (
            <section className="card draft" aria-label="Draft answer">
              <header className="card-head">
                <h2>Draft</h2>
                <span className="muted">still being checked, the final answer may differ</span>
              </header>
              <p className="answer">{draft}</p>
            </section>
          )}
          {error && (
            <p className="notice error" role="alert">
              {error}
            </p>
          )}

          <div ref={resultRef} tabIndex={-1} className="result">
            {result && (
              <>
                {result.fixture && <p className="muted fixture">Saved answer (no model was called now).</p>}
                <div className={result.baseline ? "cols two" : "cols"}>
                  <AnswerCard
                    key={result.answer_id}
                    title={result.baseline ? "GraphLens" : "Answer"}
                    answer={result.answer}
                    answerId={result.answer_id}
                    canRate={result.saved}
                    onPickLabel={pickLabel}
                  />
                  {result.baseline && <AnswerCard title="Normal RAG" answer={result.baseline} />}
                </div>
                {(result.answer.citations.length > 0 || result.answer.nodes.length > 0) && (
                  <EvidencePanel
                    key={`${result.answer_id}-${prefs.evidence_panel_open}`}
                    answer={result.answer}
                    defaultOpen={prefs.evidence_panel_open}
                    selectedLabel={selected}
                    onSelectLabel={pickLabel}
                  />
                )}
              </>
            )}
          </div>
        </>
      )}
    </div>
  );
}
