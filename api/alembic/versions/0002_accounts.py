"""Accounts: password hash, sessions, recovery codes and reset tokens (Phase 8, Part B).

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-30
"""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

UP = """
ALTER TABLE users
    ADD COLUMN password_hash text,
    ADD COLUMN home_visitor_id uuid UNIQUE REFERENCES visitors(id) ON DELETE SET NULL,
    ADD COLUMN last_login_at timestamptz;

CREATE TABLE sessions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    secret_hash text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    last_used_at timestamptz NOT NULL DEFAULT now(),
    expires_at timestamptz NOT NULL,
    revoked_at timestamptz
);
CREATE INDEX ON sessions (user_id);

CREATE TABLE recovery_codes (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    code_hash text NOT NULL,
    batch integer NOT NULL DEFAULT 1,
    created_at timestamptz NOT NULL DEFAULT now(),
    used_at timestamptz
);
CREATE INDEX ON recovery_codes (user_id) WHERE used_at IS NULL;

CREATE TABLE reset_tokens (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash text UNIQUE NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    expires_at timestamptz NOT NULL,
    used_at timestamptz
);
"""


def upgrade() -> None:
    op.execute(UP)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS reset_tokens")
    op.execute("DROP TABLE IF EXISTS recovery_codes")
    op.execute("DROP TABLE IF EXISTS sessions")
    op.execute(
        "ALTER TABLE users DROP COLUMN IF EXISTS last_login_at, "
        "DROP COLUMN IF EXISTS home_visitor_id, DROP COLUMN IF EXISTS password_hash"
    )
