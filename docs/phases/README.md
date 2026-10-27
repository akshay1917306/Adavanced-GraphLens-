# Phases

Source: blueprint v1.0 section 5.1. One phase at a time; each ends with owner
approval, a merged pull request, and a `phase-N` tag.

| Phase | Folder | Status |
|---|---|---|
| 0. Setup and decisions | [phase-0-setup](phase-0-setup/) | Approved, merged, tag `phase-0` |
| 1. Baseline RAG and evaluation set v0 | [phase-1-baseline](phase-1-baseline/) | Approved, merged, tag `phase-1` |
| 2. Extraction and graph | [phase-2-extraction](phase-2-extraction/) | Approved, merged, tag `phase-2` |
| 3. Communities and global search | [phase-3-communities](phase-3-communities/) | Approved, merged, tag `phase-3` |
| 4. Local search, router, relate, citation check | [phase-4-local-search](phase-4-local-search/) | Approved, merged, tag `phase-4` |
| 5. Product UI | [phase-5-ui](phase-5-ui/) | Built on a local branch, waiting for owner approval |
| 6. User data and hardening | phase-6-hardening | Planned |
| 7. Evaluate and launch | phase-7-launch | Planned |
| 8. v1.5 | phase-8-v1-5 | Later |

Each phase folder holds: `BRIEF.md` (goal and scope), `PREREQUISITES.md` (what the
owner prepares), `CHECKLIST.md` (acceptance checks), `PROMPT.md` (how to resume the
work with an AI assistant), `STATUS.md` (current state and next action), and
`WALKTHROUGH.md` (how it works, for a new developer).
