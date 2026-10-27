"use client";

import { useEffect, useState } from "react";
import { call } from "@/lib/client";
import type { SavedItem } from "@/lib/types";

// Answers I chose to keep, each with a short note I can change.
export default function SavedView() {
  const [items, setItems] = useState<SavedItem[] | null>(null);
  const [notes, setNotes] = useState<Record<string, string>>({});
  const [message, setMessage] = useState("");

  const [version, setVersion] = useState(0);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      const res = await call<{ items: SavedItem[] }>("/api/saved");
      if (cancelled) return;
      const list = res.ok && res.data ? res.data.items : [];
      setItems(list);
      setNotes(Object.fromEntries(list.map((i) => [i.answer_id, i.note ?? ""])));
      if (!res.ok) setMessage(res.message);
    })();
    return () => {
      cancelled = true;
    };
  }, [version]);

  async function saveNote(id: string) {
    const note = (notes[id] ?? "").trim();
    const res = await call("/api/saved", "POST", { answer_id: id, note: note || null });
    setMessage(res.ok ? "Note saved." : res.message);
  }

  async function remove(id: string) {
    const res = await call(`/api/saved/${id}`, "DELETE");
    if (res.ok) setVersion((v) => v + 1);
    else setMessage(res.message);
  }

  return (
    <section className="card" aria-labelledby="saved-title">
      <h2 id="saved-title">Saved answers</h2>
      <p role="status" className="muted">
        {message}
      </p>
      {items === null && <p>Loading…</p>}
      {items !== null && items.length === 0 && <p>Nothing saved yet. Use “Save” under an answer.</p>}
      <ul className="rows">
        {(items ?? []).map((item) => (
          <li key={item.answer_id} className="row stack">
            <strong>{item.title ?? "(no title)"}</strong>
            <p className="passage">{item.answer_text}</p>
            <label className="note">
              <span className="muted">Note (up to 500 characters)</span>
              <input
                type="text"
                maxLength={500}
                value={notes[item.answer_id] ?? ""}
                onChange={(e) => setNotes({ ...notes, [item.answer_id]: e.target.value })}
              />
            </label>
            <div className="row-actions">
              <button type="button" onClick={() => saveNote(item.answer_id)}>
                Save note
              </button>
              <button type="button" onClick={() => remove(item.answer_id)}>
                Remove
              </button>
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
