// Shapes returned by the GraphLens API (see api/app/schemas.py).

export type Mode = "local" | "global" | "relate" | "baseline";
export type Status = "answered" | "refused" | "clarify";
export type CheckStatus = "verified" | "warning" | "not_checked";

export interface Citation {
  label: string;
  kind: "text_unit" | "entity" | "community";
  title: string;
  text: string;
  source: string | null;
  ref_id: string | null;
}

export interface GraphNode {
  id: string;
  label: string;
  type: string;
  confidence: number | null;
}

export interface GraphLink {
  source: string;
  target: string;
  predicate: string;
  confidence: number | null;
}

export interface Answer {
  mode: Mode;
  status: Status;
  text: string;
  message: string | null;
  citations: Citation[];
  nodes: GraphNode[];
  links: GraphLink[];
  check_status: CheckStatus;
  model: string;
  cost_usd: number;
  latency_ms: number;
}

export interface AskResponse {
  answer_id: string;
  answer: Answer;
  baseline: Answer | null;
  fixture: boolean;
  saved: boolean;
}

export interface ApiError {
  error: { code: string; message: string };
}
