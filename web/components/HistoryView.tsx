"use client";

import { useEffect, useState } from "react";
import { call } from "@/lib/client";
import type { ConversationDetail, HistoryItem } from "@/lib/types";

interface Props {
  onAskAgain: (question: string) => void;
}

const BADGE: Record<string, string> = {
  verified: "Citations checked",
  warning: "Some statements not supported",
  not_checked: "Not checked",
};

function when(iso: string): string {
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? "" : date.toLocaleString();
}

// My past questions. Deleting a conversation removes it for good; the passages and the graph of an
// old answer are not stored, so "Ask again" runs the question again instead of re-opening it.
export default function HistoryView({ onAskAgain }: Props) {
  const [items, setItems] = useState<HistoryItem[] | null>(null);
  const [message, setMessage] = useState("");
  const [confirming, setConfirming] = useState<string | null>(null);

  const [version, setVersion] = useState(0);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      const res = await call<{ items: HistoryItem[] }>("/api/history");
      if (cancelled) return;
      setItems(res.ok && res.data ? res.data.items : []);
      if (!res.ok) setMessage(res.message);
    })();
    return () => {
      cancelled = true;
    };
  }, [version]);

  async function askAgain(id: string) {
    const res = await call<ConversationDetail>(`/api/history/${id}`);
    const question = res.data?.messages.find((m) => m.role === "user")?.content;
    if (question) onAskAgain(question);
    else setMessage(res.message || "Could not open that question.");
  }

  async function remove(id: string) {
    const res = await call(`/api/history/${id}`, "DELETE");
    setConfirming(null);
    if (res.ok) {
      setMessage("Deleted.");
      setVersion((v) => v + 1);
    } else {
      setMessage(res.message);
    }
  }

  return (
    <section className="card" aria-labelledby="history-title">
      <h2 id="history-title">My questions</h2>
      <p className="muted">Only you can see this list. Deleting removes the question and its answer for good.</p>
      <p role="status" className="muted">
        {message}
      </p>
      {items === null && <p>Loading…</p>}
      {items !== null && items.length === 0 && <p>No questions yet.</p>}
      <ul className="rows">
        {(items ?? []).map((item) => (
          <li key={item.conversation_id} className="row">
            <div>
              <strong>{item.title ?? "(no title)"}</strong>
              <div className="muted">
                {when(item.created_at)}
                {item.mode ? ` · ${item.mode}` : ""}
                {item.refused ? " · no answer" : item.check_status ? ` · ${BADGE[item.check_status]}` : ""}
              </div>
            </div>
            <div className="row-actions">
              <button type="button" onClick={() => askAgain(item.conversation_id)}>
                Ask again
              </button>
              {confirming === item.conversation_id ? (
                <>
                  <button type="button" className="danger" onClick={() => remove(item.conversation_id)}>
                    Yes, delete
                  </button>
                  <button type="button" onClick={() => setConfirming(null)}>
                    Cancel
                  </button>
                </>
              ) : (
                <button type="button" onClick={() => setConfirming(item.conversation_id)}>
                  Delete
                </button>
              )}
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
