# Verifiable Research and Technology Proposal

## 1. Core Problem Analysis
The demo must show continuous text-event ingestion, near-real-time cluster assignment, and repeatable replay/reset behavior in a package an interviewer can run locally without extra infrastructure. The main architecture risks are concurrency during join-or-create decisions, consistency between online assignment and background merge correction, and keeping the packaged demo understandable enough that the interviewer can inspect the API, the live dashboard, and the threshold-calibration workflow without reading source code first.

## 2. Verifiable Technology Recommendations
| Technology/Pattern | Rationale & Evidence |
|---|---|
| **Docker Compose** | Docker documents Compose as a way to define, configure, and run multi-container applications from a single YAML file, and its CLI supports lifecycle commands such as `up`, `down`, `logs`, and `ps`. That makes it a good packaging choice for a ZIP-distributed demo with an API service, a database, and a maintenance worker. [cite:1] [cite:2] |
| **PostgreSQL Advisory Locks** | PostgreSQL documents advisory locks as application-defined locks, with transaction-level variants released automatically at the end of the transaction. This is a good fit for serializing bucket-scoped join-or-create decisions without introducing a separate locking system in the demo baseline. [cite:3] |
| **pgvector** | The pgvector project describes itself as vector similarity search for Postgres and explicitly supports exact and approximate nearest-neighbor search, plus cosine distance and HNSW/IVFFlat indexes. That makes it suitable for a single-node demo that wants vector retrieval and relational metadata in one store. [cite:4] |
| **Server-Sent Events via `EventSource`** | MDN documents `EventSource` as a persistent HTTP connection for server-sent events in `text/event-stream` format and notes that SSE is unidirectional from server to client. That matches the demo requirement to push cluster decisions and merge updates from the server to the `LiveDashboard` without needing bi-directional browser messaging. [cite:5] |
| **FastAPI** | FastAPI documents automatic interactive API documentation at `/docs` and OpenAPI schema generation, which improves demo inspectability for interview follow-up. The official tutorial also shows that path operations can be implemented with `async def`, which is appropriate for an API that combines HTTP endpoints, SSE, and database-backed workflows. [cite:6] [cite:7] |

## 3. Browsed Sources
- [1] https://docs.docker.com/guides/docker-compose/ - Docker guide describing Compose as a way to define, configure, and run multi-container applications from a single YAML file
- [2] https://docs.docker.com/compose/intro/compose-application-model/ - Docker manual explaining the Compose file, service/network model, and `docker compose` lifecycle commands
- [3] https://www.postgresql.org/docs/17/explicit-locking.html - PostgreSQL documentation for advisory locks and transaction-level lock behavior
- [4] https://github.com/pgvector/pgvector - pgvector project README describing vector search support, distance functions, and ANN indexes
- [5] https://developer.mozilla.org/en-US/docs/Web/API/EventSource - MDN documentation for `EventSource` and SSE transport semantics
- [6] https://fastapi.tiangolo.com/tutorial/first-steps/ - FastAPI tutorial documenting automatic API docs and OpenAPI generation
- [7] https://fastapi.tiangolo.com/features/ - FastAPI features page documenting automatic docs and OpenAPI-based exploration

## 4. Assumptions
- The distributable demo will use Docker Compose for packaging, but that is a project decision for local interview delivery rather than a universal production recommendation.
- The demo will use a single embedding model cached under `.cache/`; the exact model choice and model size are project decisions and are intentionally not presented here as sourced facts.
- The initial demo baseline will use PostgreSQL plus pgvector only; replacing the vector layer with a dedicated vector engine is intentionally deferred until a future scale-out phase.
- The live dashboard is implemented as a terminal UI fed by an SSE endpoint because that keeps the artifact easy to inspect and demo in a ZIP package.
