# CR-0004: Live answers come from a separate internal search service

Status: **Approved by the owner on 2026-10-29** (Phase 7 plan, D61)
Date: 2026-10-29
Changes: **D43** (Phase 5: "the API image installs the `graphlens_pipeline` package and calls it
directly"). Affects: Phase 7 only.

## Why

D43 assumed the API and the pipeline package could live in one image. Phase 5 and Phase 6 found
that they cannot, without risk:

- the API pins `neo4j` 6.4.1 and FastAPI 0.156; the pipeline pins `neo4j` 5.28.2 and FastAPI
  0.143 (Prefect needs the older FastAPI, D21);
- the search code needs the embedding runtime (`fastembed`, about 1 GB in memory), `numpy`,
  `tiktoken`, the Qdrant client and the OpenAI client, none of which the API needs today;
- one image would make every API change rebuild a 1.4 GB image and would let a bug in the search
  code take the API (limits, tokens, history) down with it.

## Decision

Run the search code in **its own container**, built from the existing pipeline image, which already
has every pin and the local models:

- a small internal HTTP service (`serve-search`) with one route, `POST /search`, and a readiness
  route, `GET /healthz`;
- it is **not published** on any host port; only the API container can reach it, over the Compose
  network, and every call must carry a shared key (`SEARCH_SERVICE_KEY`);
- the API stays the only public entry: visitor tokens, rate limits, the daily cost cap, history and
  error shapes all stay in the API. The search service only answers one question at a time;
- the API calls it with a hard time limit, one retry only when the connection could not be opened
  (never after the request was sent, so a paid call is never repeated by accident), and a circuit
  breaker that fails fast after repeated failures;
- the answer shape is the same as the replay shape (`Answer`), so the screen does not change.

The service starts under the Compose profile `live`; the default stack still runs in replay mode and
needs no key and no model.

## Not chosen

- Forcing both package sets into one image: conflicting pins, large image, weaker isolation.
- Moving the API into the pipeline image: same size problem, and it puts public traffic next to the
  database loaders.

## Consequences

- One more container (about 1 GB of memory while the embedding model is loaded).
- A new internal contract. The API rejects a reply with unknown fields, so drift between the two
  sides is caught at run time and by tests.
- `uvicorn` is used by the service because Prefect already brings it into the pipeline image; it
  should be declared explicitly the next time the pipeline lock file changes (a lock change rebuilds
  the image layers that download the models, so it is not done for this change).
- D43 is marked as amended by this change request.
