"use client";

import { useState } from "react";
import type { Answer } from "@/lib/types";
import EvidenceGraph from "./EvidenceGraph";

interface Props {
  answer: Answer;
  selectedLabel: string | null;
  onSelectLabel: (label: string | null) => void;
}

// "Why this answer": the sources used and the small evidence graph. Text only, never HTML.
export default function EvidencePanel({ answer, selectedLabel, onSelectLabel }: Props) {
  const [nodeId, setNodeId] = useState<string | null>(null);
  const byRef = new Map(answer.citations.filter((c) => c.ref_id).map((c) => [c.ref_id as string, c]));
  const nameOf = new Map(answer.nodes.map((n) => [n.id, n.label]));
  const selectedNode = answer.nodes.find((n) => n.id === nodeId) ?? null;
  const nodePassage = selectedNode ? byRef.get(selectedNode.id) : undefined;

  return (
    <section className="panel" aria-labelledby="why-title">
      <h2 id="why-title">Why this answer</h2>

      {answer.citations.length > 0 && (
        <>
          <h3>Sources used</h3>
          <ol className="sources">
            {answer.citations.map((c) => (
              <li
                key={c.label}
                id={`source-${c.label}`}
                className={selectedLabel === c.label ? "source current" : "source"}
              >
                <button type="button" className="chip" onClick={() => onSelectLabel(c.label)}>
                  {c.label}
                </button>
                <div>
                  <strong>{c.title}</strong>
                  {c.source ? <span className="muted"> · {c.source}</span> : null}
                  <p className="passage">{c.text}</p>
                </div>
              </li>
            ))}
          </ol>
        </>
      )}

      {answer.nodes.length > 0 && (
        <>
          <h3>Connections found</h3>
          <EvidenceGraph nodes={answer.nodes} links={answer.links} selectedId={nodeId} onSelect={setNodeId} />
          <p className="legend muted">
            Circle: method · Square: dataset · Diamond: task · Triangle: metric · Rounded: paper or person
          </p>
          {selectedNode && (
            <div className="node-detail" aria-live="polite">
              <strong>{selectedNode.label}</strong> <span className="muted">({selectedNode.type})</span>
              <p className="passage">
                {nodePassage ? nodePassage.text : "This item is not quoted in the answer."}
              </p>
            </div>
          )}
          <h3>Same connections as text</h3>
          <ul className="text-graph">
            {answer.links.length === 0 && <li>No links between these items.</li>}
            {answer.links.map((l, i) => (
              <li key={`${l.source}-${l.predicate}-${l.target}-${i}`}>
                {nameOf.get(l.source) ?? l.source} — {l.predicate} → {nameOf.get(l.target) ?? l.target}
              </li>
            ))}
          </ul>
          <p className="muted">
            Items: {answer.nodes.map((n) => `${n.label} (${n.type})`).join(", ")}
          </p>
        </>
      )}
    </section>
  );
}
