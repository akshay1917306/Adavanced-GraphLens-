"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import type { ApiError, AskResponse } from "@/lib/types";
import AnswerCard from "./AnswerCard";
import EvidencePanel from "./EvidencePanel";
import ThemeToggle from "./ThemeToggle";

const MAX_CHARS = 4000;

export default function AskApp() {
  const [question, setQuestion] = useState("");
  const [compare, setCompare] = useState(false);
  const [examples, setExamples] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<AskResponse | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const resultRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetch("/api/examples")
      .then((r) => (r.ok ? r.json() : { questions: [] }))
      .then((d: { questions: string[] }) => setExamples(d.questions))
      .catch(() => setExamples([]));
  }, []);

  async function ask(text: string) {
    const trimmed = text.trim();
    if (!trimmed || busy) return;
    setBusy(true);
    setError("");
    setSelected(null);
    try {
      const res = await fetch("/api/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: trimmed, compare }),
      });
      const body = (await res.json()) as AskResponse | ApiError;
      if (!res.ok || "error" in body) {
        setResult(null);
        setError("error" in body ? body.error.message : "Something went wrong.");
      } else {
        setResult(body);
        setTimeout(() => resultRef.current?.focus(), 0);
      }
    } catch {
      setResult(null);
      setError("Could not reach the server. Is it running?");
    } finally {
      setBusy(false);
    }
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    void ask(question);
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

      <form onSubmit={submit} className="ask">
        <label htmlFor="question">Ask a question about the papers</label>
        <textarea
          id="question"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          maxLength={MAX_CHARS}
          rows={3}
          placeholder="For example: What size of model does KGT5 use in its main experiments?"
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
            <span className="muted">Saved examples:</span>
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
        {busy ? "Looking for an answer…" : ""}
      </div>
      {error && (
        <p className="notice error" role="alert">
          {error}
        </p>
      )}

      <div ref={resultRef} tabIndex={-1} className="result">
        {result && (
          <>
            {result.fixture && (
              <p className="muted fixture">Saved answer (no model was called now).</p>
            )}
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
              <EvidencePanel answer={result.answer} selectedLabel={selected} onSelectLabel={pickLabel} />
            )}
          </>
        )}
      </div>
    </div>
  );
}
