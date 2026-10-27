"use client";

import { useState } from "react";
import { call } from "@/lib/client";
import type { Answer, CheckStatus } from "@/lib/types";

const CITATION = /\[((?:[TEC]\d+)(?:\s*,\s*[TEC]\d+)*)\]/g;

const BADGE: Record<CheckStatus, { text: string; className: string }> = {
  verified: { text: "Citations checked", className: "badge ok" },
  warning: { text: "Some statements not supported", className: "badge warn" },
  not_checked: { text: "Not checked", className: "badge off" },
};

// Splits the answer into plain text and clickable source chips. React escapes the text,
// so nothing in an answer is ever interpreted as HTML.
function withChips(text: string, labels: Set<string>, onPick: (label: string) => void) {
  const parts: (string | { labels: string[]; key: number })[] = [];
  let last = 0;
  let key = 0;
  for (const match of text.matchAll(CITATION)) {
    const index = match.index ?? 0;
    if (index > last) parts.push(text.slice(last, index));
    parts.push({ labels: match[1].split(",").map((s) => s.trim()), key: key++ });
    last = index + match[0].length;
  }
  if (last < text.length) parts.push(text.slice(last));
  return parts.map((part) =>
    typeof part === "string" ? (
      part
    ) : (
      <span key={part.key}>
        {part.labels.map((label) =>
          labels.has(label) ? (
            <button key={label} type="button" className="chip inline" onClick={() => onPick(label)}>
              {label}
            </button>
          ) : (
            <span key={label} className="chip inline missing" title="Not shown in the sources">
              {label}
            </span>
          ),
        )}
      </span>
    ),
  );
}

interface Props {
  title: string;
  answer: Answer;
  answerId?: string;
  canRate?: boolean;
  onPickLabel?: (label: string) => void;
}

export default function AnswerCard({ title, answer, answerId, canRate, onPickLabel }: Props) {
  const [rating, setRating] = useState<"up" | "down" | null>(null);
  const [note, setNote] = useState("");
  const [kept, setKept] = useState(false);
  const labels = new Set(answer.citations.map((c) => c.label));
  const badge = BADGE[answer.check_status];

  async function keep() {
    const res = await call("/api/saved", "POST", { answer_id: answerId });
    setKept(res.ok);
    setNote(res.ok ? "Saved to “Saved answers”." : res.message);
  }

  async function rate(value: "up" | "down") {
    setNote("");
    try {
      const res = await fetch("/api/feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ answer_id: answerId, rating: value }),
      });
      if (res.ok) {
        setRating(value);
        setNote("Thanks, saved.");
      } else {
        setNote("Could not save your rating.");
      }
    } catch {
      setNote("Could not save your rating.");
    }
  }

  return (
    <article className="card" aria-label={title}>
      <header className="card-head">
        <h2>{title}</h2>
        <span className="muted">Mode: {answer.mode}</span>
      </header>

      {answer.status === "answered" ? (
        <>
          <p className="answer">{withChips(answer.text, labels, onPickLabel ?? (() => {}))}</p>
          <p>
            <span className={badge.className}>{badge.text}</span>
          </p>
        </>
      ) : (
        <p className="notice" role="status">
          {answer.status === "refused" ? "No answer: " : "A question for you: "}
          {answer.message ?? "The system could not answer this."}
        </p>
      )}

      {canRate && answer.status === "answered" && (
        <div className="feedback">
          <span className="muted">Was this helpful?</span>
          <button
            type="button"
            aria-label="Helpful"
            aria-pressed={rating === "up"}
            onClick={() => rate("up")}
          >
            👍 Yes
          </button>
          <button type="button" aria-label="Not helpful" aria-pressed={rating === "down"} onClick={() => rate("down")}>
            👎 No
          </button>
          <button type="button" aria-pressed={kept} onClick={keep}>
            {kept ? "Saved" : "Save"}
          </button>
          <span role="status" className="muted">
            {note}
          </span>
        </div>
      )}
    </article>
  );
}
