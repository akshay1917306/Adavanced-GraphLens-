-- Initial schema: every table and index from blueprint v1.0 section 4.4.
-- The blueprint (4.1) requires all tables in the first migration so v1.5 needs no breaking change.
-- Copied from the blueprint without changes. Do not edit; add a new migration instead.

CREATE TABLE ontologies (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name text NOT NULL,
    version integer NOT NULL,
    yaml text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (name, version)
);

CREATE TABLE corpora (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name text NOT NULL,
    description text,
    ontology_id uuid REFERENCES ontologies(id),
    active_index_version text,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE documents (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    corpus_id uuid NOT NULL REFERENCES corpora(id),
    title text,
    source_uri text,
    content_hash text NOT NULL,
    license text,
    trust_level text NOT NULL DEFAULT 'medium' CHECK (trust_level IN ('high','medium','low')),
    metadata jsonb,
    status text NOT NULL DEFAULT 'ingested',
    ingested_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (corpus_id, content_hash)
);

CREATE TABLE text_units (
    id text PRIMARY KEY,
    document_id uuid NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    ordinal integer NOT NULL,
    text text NOT NULL,
    token_count integer NOT NULL,
    content_hash text NOT NULL,
    UNIQUE (document_id, ordinal)
);

-- Pipeline runs, caches, and quality
CREATE TABLE index_runs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    corpus_id uuid NOT NULL REFERENCES corpora(id),
    index_version text NOT NULL,
    status text NOT NULL DEFAULT 'queued' CHECK (status IN ('queued','running','failed','passed_gate','published','cancelled')),
    ontology_id uuid REFERENCES ontologies(id),
    config jsonb NOT NULL,
    dry_run boolean NOT NULL DEFAULT false,
    cost_cap_usd numeric(10,2),
    cost_usd numeric(10,4) NOT NULL DEFAULT 0,
    tokens_in bigint NOT NULL DEFAULT 0,
    tokens_out bigint NOT NULL DEFAULT 0,
    stats jsonb,
    started_at timestamptz,
    finished_at timestamptz,
    published_at timestamptz,
    UNIQUE (corpus_id, index_version)
);

CREATE TABLE run_stages (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id uuid NOT NULL REFERENCES index_runs(id) ON DELETE CASCADE,
    stage text NOT NULL,
    status text NOT NULL DEFAULT 'pending',
    items_total integer,
    items_done integer NOT NULL DEFAULT 0,
    cost_usd numeric(10,4) NOT NULL DEFAULT 0,
    error text,
    started_at timestamptz,
    finished_at timestamptz,
    UNIQUE (run_id, stage)
);

CREATE TABLE extraction_cache (
    cache_key text PRIMARY KEY,
    result jsonb NOT NULL,
    tokens_in integer,
    tokens_out integer,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE resolution_decisions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id uuid NOT NULL REFERENCES index_runs(id) ON DELETE CASCADE,
    entity_a text NOT NULL,
    entity_b text NOT NULL,
    score real,
    method text NOT NULL CHECK (method IN ('auto_merge','llm','rejected')),
    decision text NOT NULL CHECK (decision IN ('merge','keep_separate')),
    rationale text,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE quality_checks (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id uuid NOT NULL REFERENCES index_runs(id) ON DELETE CASCADE,
    check_name text NOT NULL,
    value numeric,
    threshold numeric,
    passed boolean NOT NULL,
    details jsonb,
    created_at timestamptz NOT NULL DEFAULT now()
);

-- Identity and preferences
CREATE TABLE users (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    email text UNIQUE NOT NULL,
    display_name text,
    role text NOT NULL DEFAULT 'user' CHECK (role IN ('user','admin')),
    created_at timestamptz NOT NULL DEFAULT now(),
    deleted_at timestamptz
);

CREATE TABLE visitors (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid REFERENCES users(id),
    ip_hash text,
    first_seen_at timestamptz NOT NULL DEFAULT now(),
    last_seen_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE preferences (
    visitor_id uuid PRIMARY KEY REFERENCES visitors(id) ON DELETE CASCADE,
    default_corpus_id uuid REFERENCES corpora(id),
    default_mode text NOT NULL DEFAULT 'auto' CHECK (default_mode IN ('auto','local','global','relate','baseline')),
    theme text NOT NULL DEFAULT 'system' CHECK (theme IN ('system','light','dark')),
    evidence_panel_open boolean NOT NULL DEFAULT true,
    updated_at timestamptz NOT NULL DEFAULT now()
);

-- Conversations and answer data
CREATE TABLE conversations (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    visitor_id uuid NOT NULL REFERENCES visitors(id) ON DELETE CASCADE,
    corpus_id uuid REFERENCES corpora(id),
    title text,
    share_token text UNIQUE,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    deleted_at timestamptz
);

CREATE TABLE messages (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id uuid NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role text NOT NULL CHECK (role IN ('user','assistant')),
    content text NOT NULL,
    mode_requested text CHECK (mode_requested IN ('auto','local','global','relate','baseline')),
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE retrieval_traces (
    message_id uuid NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    kind text NOT NULL CHECK (kind IN ('text_unit','entity','relationship','community')),
    ref_id text NOT NULL,
    rank smallint,
    score real,
    cited boolean NOT NULL DEFAULT false,
    PRIMARY KEY (message_id, kind, ref_id)
);

CREATE TABLE answer_meta (
    message_id uuid PRIMARY KEY REFERENCES messages(id) ON DELETE CASCADE,
    mode_used text NOT NULL CHECK (mode_used IN ('local','global','relate','baseline')),
    router_confidence real,
    model text NOT NULL,
    index_version text NOT NULL,
    ttft_ms integer,
    latency_ms integer,
    tokens_in integer,
    tokens_out integer,
    cost_usd numeric(8,5),
    nodes_in_context integer,
    edges_in_context integer,
    citation_status text CHECK (citation_status IN ('verified','warning','not_checked')),
    unsupported_statements jsonb,
    refused boolean NOT NULL DEFAULT false,
    partial boolean NOT NULL DEFAULT false,
    cache_hit boolean NOT NULL DEFAULT false
);

-- Feedback, saved answers, and administration
CREATE TABLE feedback (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id uuid NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    visitor_id uuid NOT NULL REFERENCES visitors(id) ON DELETE CASCADE,
    rating text NOT NULL CHECK (rating IN ('up','down')),
    reason text CHECK (reason IN ('wrong_answer','missing_evidence','wrong_connection','too_slow','other')),
    comment text,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (message_id, visitor_id)
);

CREATE TABLE saved_answers (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    visitor_id uuid NOT NULL REFERENCES visitors(id) ON DELETE CASCADE,
    message_id uuid NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    note text,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (visitor_id, message_id)
);

CREATE TABLE admin_audit_log (
    id bigserial PRIMARY KEY,
    user_id uuid REFERENCES users(id),
    action text NOT NULL,
    target text,
    created_at timestamptz NOT NULL DEFAULT now()
);

-- Evaluation
CREATE TABLE eval_sets (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name text NOT NULL,
    kind text NOT NULL CHECK (kind IN ('local','global','relate','unanswerable','extraction','resolution','communities')),
    version integer NOT NULL DEFAULT 1,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (name, version)
);

CREATE TABLE eval_questions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    set_id uuid NOT NULL REFERENCES eval_sets(id) ON DELETE CASCADE,
    question text NOT NULL,
    expected jsonb,
    supporting_unit_ids text[],
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE eval_runs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    index_run_id uuid REFERENCES index_runs(id),
    git_sha text NOT NULL,
    config jsonb NOT NULL,
    metrics jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE eval_results (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    eval_run_id uuid NOT NULL REFERENCES eval_runs(id) ON DELETE CASCADE,
    question_id uuid NOT NULL REFERENCES eval_questions(id),
    mode text NOT NULL,
    answer text,
    scores jsonb,
    cost_usd numeric(8,5),
    latency_ms integer
);

-- Indexes for the main access paths
CREATE INDEX ON text_units (document_id, ordinal);

CREATE INDEX ON documents (corpus_id, status);

CREATE INDEX ON index_runs (corpus_id, started_at DESC);

CREATE INDEX ON resolution_decisions (run_id, decision);

CREATE INDEX ON conversations (visitor_id, updated_at DESC) WHERE deleted_at IS NULL;

CREATE INDEX ON messages (conversation_id, created_at);

CREATE INDEX ON retrieval_traces (kind, ref_id);

CREATE INDEX ON feedback (rating, created_at);

CREATE INDEX ON answer_meta (mode_used, citation_status);

CREATE INDEX ON visitors (user_id);
