# CR-0001: Simplified dashboard for v1

Status: **Proposed** (owner has asked for it; not yet approved as a Change Request)
Date: 2026-10-23
Changes: blueprint Part 3 (UX and UI Design), sections 3.3, 3.4, 3.6, 3.7. Affects Phase 5 only.

## Why

The blueprint dashboard has many screens, five query modes, and an admin area. The owner
finds it too complex to understand and to explain to an interviewer. A dashboard that is
easy to explain makes the project's idea (answers with proof, graph beats plain RAG)
easier to show.

## Proposal

Phase 5 builds a **simple view first**: one main screen and one compare switch.

| Part | Simple view |
|---|---|
| Ask screen | Question box, answer with numbered source chips, a "Why this answer" panel |
| Why this answer | The sources used, plus a **small evidence graph** (about 4 to 6 dots, shapes by type, line width by strength, dashed for low confidence). Selecting a dot shows its source passage |
| Mode | Automatic by default; one **Compare with normal RAG** switch shows both answers side by side |
| Trust | One badge: "Citations checked" or "Some statements not supported" |
| Feedback | Thumbs up or down |

Moved to "later view" (kept in the backlog, built only if time allows): the full graph
explorer (300 nodes, filters, table view), community tree, manual mode chips (Local,
Global, Relate), entity pages. The small evidence graph above **stays in v1**, because the
blueprint treats the graph as core evidence, not an extra. It still needs a text
alternative (list of the same dots and links) for accessibility.

## What does not change

All backend behaviour, search modes, citation check, refusal, security rules and the
evaluation plan stay as in the blueprint. Only what is shown on screen is reduced. The
admin run and quality screens stay read-only and are not part of the demo path.

## Risks

- Hiding the graph view weakens the "evidence" story. Mitigation: keep the small
  connection chain in "Why this answer".
- Removing mode chips reduces control. Mitigation: the router still picks the mode and the
  chosen mode is shown as text.

## Decision

Pending owner approval. Until approved, the blueprint design stays the plan of record.
