# Demo Runbook

## What the Interviewer Needs
- Docker with Compose support
- The unzipped demo folder

## First-Time Startup
From the project root:

```bash
docker compose up --build
```

This starts:
- `api`
- `db`
- `maintenance`

On the first run, the packaged Docker demo uses the default `embedding_backend=sentence-transformers` setting and downloads the configured model into `.cache/models/sentence-transformers`. That warmup is expected and should happen only once unless `.cache/` is deleted. The demo also computes a deterministic stable-projection vector for each event and cluster, so if the semantic model is unavailable the system can pivot to `vector_mode=stable_projection` without losing clustering capability.

## API Docs
After startup, open:

```text
http://127.0.0.1:8000/docs
```

This is the FastAPI interactive API surface for ingest and inspection endpoints.

## Core Demo Commands
Run these from the API container context:

```bash
docker compose exec api demo replay --rebase-now
docker compose exec api demo watch
docker compose exec api demo send "The login queue is exploding again" --source manual
docker compose exec api demo reset
docker compose exec api demo calibrate
```

## Recommended Demo Flow
1. Start the stack with `docker compose up --build`.
2. Open the API docs at `/docs`.
3. In one terminal, run:

```bash
docker compose exec api demo watch
```

   The dashboard renders three panes without polling the database:
   - active clusters
   - recent merges
   - recent SSE event log

4. In another terminal, run:

```bash
docker compose exec api demo replay --rebase-now
```

5. Point out how exact duplicates join quickly, paraphrases join semantically, and draft-band events create `draft` clusters with stored parent evidence.
6. Send one or two live manual events with `demo send`.
7. Run `demo reset` to prove the database can be restored to the live baseline story without deleting Docker volumes.
8. If you want to re-stream the clustering decisions from scratch, run `demo replay --rebase-now` again. That command clears runtime state first, then replays the story through the API using fresh timestamps inside the draft-merge window while preserving event order.

## Larger Week-Long Sample
Use the generated 1,000-event story for stress testing:

```bash
docker compose exec api demo replay --story-path data/week_story_1000.jsonl --rebase-now
docker compose exec api demo calibrate --story-path data/week_story_1000.jsonl --labels-path data/week_story_1000.labels.json
```

Notes:
- `week_story_1000.jsonl` spans a raw calendar week on disk
- `--rebase-now` compresses that story into the recent draft-merge window for live replay
- event order is preserved and original timestamps are copied into event metadata as `original_occurred_at`

## `.cache/` Model Directory
- Location: `./.cache/`
- Purpose: store the cached sentence-transformers model and local manifest between runs
- Git behavior: `.cache/` is included in `.gitignore`
- Container behavior: `.cache/` is mounted into the API container so model downloads persist across restarts and resets

The reset flow does not touch `.cache/`; it resets database state only.

## Degraded Mode
- Default config uses `embedding_backend=sentence-transformers` and `vector_mode=auto`.
- `auto` means: use the semantic vector when the transformer backend is available, otherwise pivot to the stable-projection vector.
- For a deterministic degraded-mode walkthrough, set `vector_mode=stable_projection` in `config/demo.yaml` and restart the stack.
- Projection vectors are always stored in `projection_embeddings`.
- Semantic vectors are stored separately in `semantic_embeddings` only when the model is available.
- If semantic embedding is unavailable during ingest, the demo leaves the semantic table entry empty instead of copying projection data into it.
- The `MaintenanceWorker` retries loading the semantic backend and backfills missing semantic event vectors and cluster centroids later when semantic embedding becomes available again.
- The system switches to semantic retrieval only when the shared `semantic_ready_for_active_window` flag is true, which means missing semantic rows in the active reuse window have reached zero.
- Because the two vector paths live in separate tables, the pivot changes retrieval/scoring behavior without polluting semantic storage or requiring a schema reset.

## Expected Baseline Behaviors
- Repeat events reuse the same cluster immediately through the fingerprint fast path.
- Strong paraphrases join based on the recency-adjusted semantic score.
- Scores in the `0.60-0.70` range create `draft` clusters.
- Later merges happen only when post-hoc evidence is stronger than the original rejected online evidence.
- `demo reset` restores the live baseline story immediately.
