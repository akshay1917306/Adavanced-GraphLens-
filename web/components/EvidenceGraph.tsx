"use client";

import { useId } from "react";
import type { GraphLink, GraphNode } from "@/lib/types";

// A small evidence graph: at most six dots. Shape tells the type, a dashed line tells a
// low-confidence link. Everything here is also available as a text list (see EvidencePanel).

const W = 360;
const H = 280;
const R = 15;

function shorten(text: string, max = 16): string {
  return text.length > max ? `${text.slice(0, max - 1)}…` : text;
}

function place(count: number): { x: number; y: number }[] {
  if (count === 1) return [{ x: W / 2, y: H / 2 }];
  return Array.from({ length: count }, (_, i) => {
    const angle = (2 * Math.PI * i) / count - Math.PI / 2;
    return { x: W / 2 + 120 * Math.cos(angle), y: H / 2 - 8 + 85 * Math.sin(angle) };
  });
}

function Shape({ type, x, y }: { type: string; x: number; y: number }) {
  switch (type) {
    case "Dataset":
      return <rect x={x - R} y={y - R} width={2 * R} height={2 * R} rx={2} />;
    case "Task":
      return <polygon points={`${x},${y - R - 3} ${x + R + 3},${y} ${x},${y + R + 3} ${x - R - 3},${y}`} />;
    case "Metric":
      return <polygon points={`${x},${y - R - 2} ${x + R + 2},${y + R} ${x - R - 2},${y + R}`} />;
    case "Paper":
    case "Author":
      return <rect x={x - R} y={y - R} width={2 * R} height={2 * R} rx={9} />;
    default:
      return <circle cx={x} cy={y} r={R} />;
  }
}

interface Props {
  nodes: GraphNode[];
  links: GraphLink[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}

export default function EvidenceGraph({ nodes, links, selectedId, onSelect }: Props) {
  const markerId = useId();
  const spots = place(nodes.length);
  const at = new Map(nodes.map((n, i) => [n.id, spots[i]]));

  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      className="graph"
      role="group"
      aria-label="Evidence graph. The same dots and links are listed as text below."
    >
      <defs>
        <marker id={markerId} viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto">
          <path d="M0,0 L10,5 L0,10 z" className="graph-arrow" />
        </marker>
      </defs>
      {links.map((link, i) => {
        const a = at.get(link.source);
        const b = at.get(link.target);
        if (!a || !b) return null;
        const dx = b.x - a.x;
        const dy = b.y - a.y;
        const len = Math.hypot(dx, dy) || 1;
        const x1 = a.x + (dx / len) * (R + 4);
        const y1 = a.y + (dy / len) * (R + 4);
        const x2 = b.x - (dx / len) * (R + 8);
        const y2 = b.y - (dy / len) * (R + 8);
        const low = link.confidence !== null && link.confidence < 0.5;
        return (
          <g key={`${link.source}-${link.predicate}-${link.target}-${i}`}>
            <line
              x1={x1}
              y1={y1}
              x2={x2}
              y2={y2}
              className="graph-link"
              strokeDasharray={low ? "5 4" : undefined}
              markerEnd={`url(#${markerId})`}
            />
            <text x={(x1 + x2) / 2} y={(y1 + y2) / 2 - 3} className="graph-predicate" textAnchor="middle">
              {link.predicate}
            </text>
          </g>
        );
      })}
      {nodes.map((node) => {
        const p = at.get(node.id);
        if (!p) return null;
        const selected = node.id === selectedId;
        return (
          <g
            key={node.id}
            className={`graph-node${selected ? " selected" : ""}`}
            role="button"
            tabIndex={0}
            aria-pressed={selected}
            aria-label={`${node.label}, ${node.type}`}
            onClick={() => onSelect(node.id)}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                onSelect(node.id);
              }
            }}
          >
            <title>{`${node.label} (${node.type})`}</title>
            <Shape type={node.type} x={p.x} y={p.y} />
            <text x={p.x} y={p.y + R + 14} textAnchor="middle" className="graph-label">
              {shorten(node.label)}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
