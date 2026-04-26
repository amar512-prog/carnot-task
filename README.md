# Recent-Event Clustering Demo

A distributable interview demo that continuously ingests text events, clusters similar recent events, exposes live decisions over an API plus SSE stream, and includes replay, reset, and threshold-calibration workflows.

## Stack
- FastAPI
- PostgreSQL + pgvector
- Python CLI with Typer + Rich
- Docker Compose for one-command local startup

## Quick Start
```bash
docker compose up --build
docker compose exec ollama ollama pull qwen3:4b-thinking
```

In another shell:

```bash
docker compose exec api demo watch
docker compose exec api demo replay --rebase-now
```

`demo watch` renders the live stream, active cluster state, and recent merges side by side.

Restore the live baseline story without removing Docker volumes:

```bash
docker compose exec api demo reset
```

Calibrate thresholds from the labeled story:

```bash
docker compose exec api demo calibrate
```

Replay the larger week-long sample in a fresh demo window:

```bash
docker compose exec api demo replay --story-path data/week_story_1000.jsonl --rebase-now
docker compose exec api demo calibrate --story-path data/week_story_1000.jsonl --labels-path data/week_story_1000.labels.json
```

## API
- Swagger UI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- Event stream: `GET /events/stream`

## Model Cache
- Location: `./.cache/`
- Purpose: stores the configured sentence-transformers model and manifest metadata for the primary semantic vector path
- Git behavior: `.cache/` is ignored in `.gitignore`
- Reset behavior: `demo reset` does not touch `.cache/`

In the packaged Docker demo, the default `embedding_backend` is `sentence-transformers`, so the first run warms the local cache by downloading the configured model into `.cache/models/sentence-transformers`. Manifest metadata stays alongside that cache under `.cache/models`. The system also maintains a deterministic stable-projection vector for every event and cluster.

Projection and semantic vectors are stored separately:
- projection vectors are always written to `projection_embeddings`
- semantic vectors are written to `semantic_embeddings` only when the model is available
- if the semantic model is unavailable, the system does **not** copy projection vectors into semantic storage
- the `MaintenanceWorker` backfills missing semantic event and cluster vectors later when semantic embedding becomes available again
- a shared `semantic_ready_for_active_window` flag keeps online retrieval on projection until missing semantic rows in the active horizon reach zero

If the transformer backend is unavailable, or if `vector_mode` is forced to `stable_projection`, clustering pivots to that sparse bag-of-words projection instead of a cryptographic hash.

## Important Paths
- Demo config: [config/demo.yaml](config/demo.yaml)
- Baseline story: [data/baseline_story.jsonl](data/baseline_story.jsonl)
- Story labels: [data/baseline_story.labels.json](data/baseline_story.labels.json)
- Week-long sample: [data/week_story_1000.jsonl](data/week_story_1000.jsonl)
- Week-long sample labels: [data/week_story_1000.labels.json](data/week_story_1000.labels.json)
- Spec pack: [specs/recent-event-clustering-demo](specs/recent-event-clustering-demo)
- Runbook: [docs/demo-runbook.md](docs/demo-runbook.md)

## Technical Deep Dives
- Scoring math: [docs/scoring-math.md](docs/scoring-math.md)
- Calibration workflow: [docs/calibration-playbook.md](docs/calibration-playbook.md)
- Interview presentation guide: [docs/interview-walkthrough.md](docs/interview-walkthrough.md)
- Architecture design: [specs/recent-event-clustering-demo/design.md](specs/recent-event-clustering-demo/design.md)
- Core clustering service: [src/demo/services/clustering_service.py](src/demo/services/clustering_service.py)
- Reset behavior: [src/demo/services/reset_service.py](src/demo/services/reset_service.py)
