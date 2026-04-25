# Requirements Document

## Introduction
This specification defines a distributable demo for recent-event clustering. The demo is intended for interview follow-up: it must be easy to run locally, easy to replay deterministically, and precise about why the system joined an existing cluster, created a draft cluster, or merged draft clusters later with stronger evidence.

## Glossary
- **IngestionAPI**: HTTP and SSE surface for ingesting events and observing live decisions.
- **ClusteringService**: Decision engine that computes similarity, applies recency decay, and chooses join versus create-draft.
- **ClusterRepository**: Persistence boundary for clusters, vector candidate lookup, exemplars, and merge audit rows.
- **EventRepository**: Persistence boundary for immutable events, fingerprints, and replay metadata.
- **MaintenanceWorker**: Background worker that revisits recent draft clusters and merges only with stronger evidence.
- **ReplayCLI**: CLI entrypoint for replay, watch, send, reset, and calibrate workflows.
- **LiveDashboard**: Terminal view that renders live decisions from the SSE stream.
- **ThresholdCalibrator**: Offline tuning tool that derives threshold recommendations from labeled replay data.
- **ResetService**: Service that resets DB state and restores the deterministic baseline story.
- **EmbeddingModelCache**: Filesystem location and load path for the local embedding model.

## Requirements

### Requirement 1: Event Ingest and Online Assignment
**Description**: The demo must ingest text events and return an immediate cluster decision.

#### Acceptance Criteria
1. WHEN a client submits a valid event to the **IngestionAPI**, THE **IngestionAPI** SHALL persist the event through the **EventRepository** and return a response containing `cluster_id`, `decision`, `confidence`, and score details.
2. WHEN the **ClusteringService** processes an event, THE **ClusteringService** SHALL evaluate only clusters whose `last_seen_at` is within the configured maximum reuse age.
3. WHEN two similar events are processed concurrently in the same similarity bucket, THE **ClusteringService** SHALL serialize the join-or-create decision using a PostgreSQL advisory lock scoped to that bucket.

### Requirement 2: Exact Dedupe and Idempotency
**Description**: The online path must avoid unnecessary vector work for obvious repeats and support replay safety.

#### Acceptance Criteria
1. WHEN the **ClusteringService** finds an existing normalized fingerprint match for a recent event, THE **ClusteringService** SHALL join that event to the existing cluster without running vector retrieval.
2. WHEN the **IngestionAPI** receives an already-seen `event_id`, THE **EventRepository** SHALL treat the request as idempotent and SHALL NOT create a duplicate event or duplicate cluster membership.

### Requirement 3: Configurable Draft Band
**Description**: Threshold-driven behavior must come from shared configuration rather than hard-coded constants.

#### Acceptance Criteria
1. WHEN the demo starts, THE **IngestionAPI**, **MaintenanceWorker**, **ReplayCLI**, and **ThresholdCalibrator** SHALL load `join_threshold`, `draft_score_min`, `draft_score_max`, `merge_evidence_threshold`, `semantic_floor`, `time_decay_half_life_minutes`, and `max_reuse_age_minutes` from one checked-in config file.
2. WHEN the **ClusteringService** computes a `final_score` between `draft_score_min` and `draft_score_max`, THE **ClusteringService** SHALL create a new cluster with status `draft` and persist the best rejected candidate cluster as evidence for later review.
3. WHEN the **ClusteringService** computes a `final_score` above `join_threshold`, THE **ClusteringService** SHALL join the highest-scoring eligible recent cluster.

### Requirement 4: Conservative Online Decisions and Stronger-Evidence Merges
**Description**: The background merge path must refine the online result without contradicting it.

#### Acceptance Criteria
1. WHEN the **MaintenanceWorker** evaluates draft clusters for merging, THE **MaintenanceWorker** SHALL require evidence stronger than the original rejected online event-to-cluster score.
2. WHEN two draft clusters only share a previously rejected near-threshold score, THE **MaintenanceWorker** SHALL NOT merge them on that score alone.
3. WHEN the **MaintenanceWorker** merges draft clusters, THE **ClusterRepository** SHALL persist merge evidence and merge history for later inspection.

### Requirement 5: Resettable Baseline Story and Replay Flow
**Description**: The interviewer must be able to rerun the demo repeatedly without manual volume deletion.

#### Acceptance Criteria
1. WHEN an operator runs `demo replay`, THE **ReplayCLI** SHALL load the deterministic baseline story in the documented order and send it through the **IngestionAPI**.
2. WHEN an operator runs `demo reset`, THE **ResetService** SHALL wipe mutable event and cluster state, preserve schema and extensions, and re-insert the baseline story without requiring Docker volume removal.
3. WHEN the baseline story is restored, THE **ReplayCLI** SHALL be able to rerun the same story and produce the same sequence of cluster decisions for the same configuration.
4. WHEN an operator runs `demo replay --rebase-now`, THE **ReplayCLI** SHALL preserve event order but SHALL compress or shift the replay timestamps into the recent draft-merge window so the replayed story is eligible for post-hoc draft merging during the live demo.
5. WHEN an operator provides `--story-path`, THE **ReplayCLI** SHALL replay that alternate JSONL story without requiring the checked-in baseline story to be overwritten.

### Requirement 6: Live Demo Observability
**Description**: The demo must expose live state transitions in a form that is easy to present.

#### Acceptance Criteria
1. WHEN the **IngestionAPI** produces an assignment or merge event, THE **IngestionAPI** SHALL publish it to `GET /events/stream` as server-sent events.
2. WHEN the **LiveDashboard** is connected to the event stream, THE **LiveDashboard** SHALL display incoming events, decisions, active clusters, and recent merges without polling the database directly.
3. WHEN an interviewer opens the API docs, THE **IngestionAPI** SHALL expose interactive HTTP documentation for the ingest and inspection endpoints.

### Requirement 7: Threshold Calibration from Labeled Replay Data
**Description**: The demo must include a reproducible way to justify the threshold choices from the same story data used in the walkthrough.

#### Acceptance Criteria
1. WHEN an operator runs `demo calibrate`, THE **ThresholdCalibrator** SHALL sweep candidate values for `join_threshold`, `draft_score_min`, and `merge_evidence_threshold` against labeled replay data, and SHALL derive `draft_score_max` from the candidate `join_threshold` so the draft band remains anchored to the join boundary.
2. WHEN the calibration run completes, THE **ThresholdCalibrator** SHALL emit a report containing the recommended threshold set, the evaluated search space, and clustering quality metrics.
3. WHEN an operator provides `--story-path` and `--labels-path`, THE **ThresholdCalibrator** SHALL calibrate against those alternate labeled files instead of the default baseline paths from config.

### Requirement 8: Local Embedding Model Cache and Documentation
**Description**: The packaged demo must make model download behavior explicit and repeatable.

#### Acceptance Criteria
1. WHEN the **ClusteringService** needs the embedding model, THE **EmbeddingModelCache** SHALL load it from the project `.cache/` directory if present and SHALL create that cache on first run if absent.
2. WHEN the demo documentation is read, THE companion runbook SHALL explain where `.cache/` lives, why it is gitignored, and what first-run warmup behavior the interviewer should expect.
3. WHEN semantic model availability is limited, THE **EventRepository** and **ClusterRepository** SHALL keep persisting projection vectors in dedicated projection storage, SHALL leave missing semantic vectors absent instead of copying projection vectors into semantic storage, and THE **MaintenanceWorker** SHALL backfill the missing semantic rows later when semantic embedding becomes available again.
4. WHEN the system is configured to prefer semantic retrieval, THE **MaintenanceWorker** SHALL set a shared `semantic_ready_for_active_window` flag to true only after missing semantic event rows and cluster centroid rows in the active reuse horizon reach zero, and THE **ClusteringService** SHALL keep using projection retrieval until that flag is true.
