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

export interface HistoryItem {
  conversation_id: string;
  title: string | null;
  created_at: string;
  answer_id: string | null;
  mode: Mode | null;
  check_status: CheckStatus | null;
  refused: boolean;
}

export interface ConversationDetail {
  conversation_id: string;
  title: string | null;
  created_at: string;
  messages: { id: string; role: "user" | "assistant"; content: string }[];
}

export interface SavedItem {
  answer_id: string;
  note: string | null;
  title: string | null;
  answer_text: string;
  saved_at: string;
}

export type ThemeChoice = "system" | "light" | "dark";

export interface Preferences {
  theme: ThemeChoice;
  default_mode: "auto" | "local" | "global" | "relate" | "baseline";
  evidence_panel_open: boolean;
}

export interface DeletedCounts {
  conversations: number;
  saved_answers: number;
  ratings: number;
}
