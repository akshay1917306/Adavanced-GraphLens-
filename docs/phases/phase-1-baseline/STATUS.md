# Phase 1 status

Last updated: 2026-10-23

## State

**Started (planning and docs only).** No pipeline code written yet.

## Completed

- Phase 0 approved by the owner, merged to `main` (fast-forward, commit 2f4a51c) and
  tagged `phase-0`. CI was green (api, web, compose).
- D3 closed: question answering (QA) papers from the ACL Anthology, CC BY only.
- Phase 1 brief, prerequisites, checklist and resume prompt written.

## Current work

Waiting for the owner on three items below. Nothing else is in progress.

## Blockers and decisions waiting for the owner

1. Permission to download about 25 CC BY QA papers from the ACL Anthology (size about 15 MB).
2. `OPENAI_API_KEY` in the local `.env` and a spending limit in the OpenAI dashboard.
3. Approval of Change Request CR-0001 (simpler dashboard) so Phase 5 plans for it.

## Exact next action

1. Owner answers the three items above.
2. Claude builds the license manifest and download script, then downloads the papers.
3. Ingest, then chunking, embeddings, baseline answer, flow, questions, results table.

## Local state

Branch `phase-1/baseline` has local docs commits only; nothing from Phase 1 is pushed yet.
