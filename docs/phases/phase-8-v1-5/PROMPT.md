# Phase 8 resume prompt

Continue GraphLens Phase 8 (v1.5: faster answers, sign-in, bigger corpus). Read
`docs/phases/phase-8-v1-5/STATUS.md` first, then `BRIEF.md`. Standing rules: one phase at a time with
approval gates; never push without the owner's yes; never force-push; the owner's OpenAI key lives
only in the git-ignored `.env`, is never printed or asked for in chat; show a dry-run estimate and
wait for a "yes" before every paid batch (caps in D73); no downloads without a yes (name and size);
never raise spend limits; speak simple Roman Marathi with English terms; code, docs and commits in
English; do not claim "secure" or "production-ready"; never hide a missed target; end with the A to J
report. Everything runs in Docker; the repository folder is `Adavanced-GraphLens-`. Shell tips: write
long files with the Write tool, not heredocs; patch files with a small script in the scratchpad; the
pipeline image needs `graphlens_pipeline` and `tests` mounted to test new code; PowerShell for
`docker compose run -v ...`; GitHub PRs and CI go through the REST API with a token from
`git credential fill` (never printed).
