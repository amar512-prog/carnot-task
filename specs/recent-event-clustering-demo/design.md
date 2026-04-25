# Design Document

## Overview
This design keeps the demo architecture simple enough for a ZIP-distributed interview artifact while still addressing the important system-design concerns: deterministic replay, bucket-level concurrency control, configurable draft-band behavior, and a background merge path that uses stronger evidence instead of contradicting the online path. The demo remains single-node and intentionally uses PostgreSQL plus pgvector as the only stateful backend.

## Design Principles
- Single responsibility
- Shared configuration for thresholds and commands
- Deterministic replay and reset behavior
- Observable decision evidence
- Background correction must strengthen, not contradict, the online path

## Shared Configuration

**Location**: `config/demo.yaml`

```yaml
join_threshold: 0.70
draft_score_min: 0.60
draft_score_max: 0.70
merge_evidence_threshold: 0.85
semantic_floor: 0.55
time_decay_half_life_minutes: 60
max_reuse_age_minutes: 180
candidate_limit: 30
draft_merge_window_minutes: 15
maintenance_interval_minutes: 5
embedding_dimension: 1024
embedding_backend: sentence-transformers
vector_mode: auto
embedding_model_id: codefuse-ai/F2LLM-v2-0.6B
baseline_story_path: data/baseline_story.jsonl
baseline_labels_path: data/baseline_story.labels.json
model_cache_dir: .cache/models
```

**Rules**:
- `draft_score_max` is the exclusive upper bound of the draft band and is expected to equal `join_threshold` in the default config.
- `semantic_floor` is the minimum raw semantic similarity allowed before a candidate can be considered eligible.
- `merge_evidence_threshold` applies to post-hoc cluster-to-cluster evidence, not to the original online event-to-cluster score.
- `vector_mode` may be `auto`, `semantic`, or `stable_projection`. `auto` prefers semantic vectors and pivots to stable-projection vectors when semantic model availability is limited.
- The online system may use semantic retrieval only when the shared `semantic_ready_for_active_window` flag is true.

## Scoring Model

### Core Score
For each candidate cluster:

```text
time_weight = exp(-ln(2) * age_minutes / time_decay_half_life_minutes)
semantic_score = max(
  cosine(event_embedding, cluster.active_centroid_embedding),
  max cosine(event_embedding, exemplar_embedding_i)
)
final_score = semantic_score * time_weight
```

The active centroid/exemplar path is selected by `vector_mode`. The demo stores projection and semantic vectors separately:
- `projection_embeddings` is always populated for events and clusters
- `semantic_embeddings` is populated only when the semantic model is available
- degraded mode never copies projection vectors into semantic storage
- the **MaintenanceWorker** backfills missing semantic event vectors and cluster centroids later when semantic embedding becomes available again
- the **ClusteringService** stays on projection retrieval until the shared readiness flag confirms that the active reuse horizon has no missing semantic rows

### Decision Rules
- If `event_id` already exists, return the previous decision idempotently.
- If a normalized fingerprint match exists in an eligible recent cluster, join immediately.
- Else query up to `candidate_limit` recent clusters from pgvector ordered by cosine distance.
- Discard candidates with `semantic_score < semantic_floor`.
- If the best candidate has `final_score >= join_threshold`, join that cluster.
- If `draft_score_min <= final_score < draft_score_max`, create a new `draft` cluster and record the rejected best candidate as `candidate_parent_cluster_id`, `candidate_parent_score`, and the score breakdown.
- If `final_score < draft_score_min`, create a new `draft` cluster with no candidate parent.

### Merge-Evidence Rules
The **MaintenanceWorker** may merge recent `draft` clusters only when:
- cluster-to-cluster evidence exceeds `merge_evidence_threshold`, and
- that evidence is stronger than the original rejected online event-to-cluster score stored on the draft cluster, and
- at least one corroborating signal is present:
  - exemplar-to-exemplar agreement,
  - repeated later linking events,
  - or shared extracted keywords/entities above a configured bound.

The **MaintenanceWorker** MUST NOT merge solely because an online score landed inside the `0.60-0.70` draft band.

## Component Specifications

### Component: IngestionAPI
**Purpose**: Accept events, expose cluster-inspection endpoints, and stream live decision updates.
**Location**: [src/demo/api/main.py](../../src/demo/api/main.py)

**Interface**:
```text
POST /events
GET /clusters/{cluster_id}
GET /clusters?status={status}&since={timestamp}
GET /events/stream

Implements: Req 1.1, Req 2.2, Req 6.1, Req 6.3
```

**Dependencies**:
- **ClusteringService**: compute join/create decisions
- **EventRepository**: enforce event idempotency
- **ClusterRepository**: serve inspection endpoints

**Data Model**:
```text
EventRequest {
  event_id: string
  source: string
  occurred_at: datetime
  text: string
  metadata: object | null
}

EventResponse {
  event_id: string
  cluster_id: string
  decision: "joined_existing_cluster" | "created_new_cluster"
  cluster_status: "draft" | "stable"
  confidence: float
  score: {
    semantic_score: float | null
    time_weight: float | null
    final_score: float | null
    candidate_parent_cluster_id: string | null
    candidate_parent_score: float | null
  }
}
```

### Component: ClusteringService
**Purpose**: Normalize events, compute scores, and decide join versus create-draft.
**Location**: [src/demo/services/clustering_service.py](../../src/demo/services/clustering_service.py)

**Interface**:
```text
assign_event(conn, event) -> AssignmentResult

Implements: Req 1.2, Req 1.3, Req 2.1, Req 3.2, Req 3.3, Req 4.1, Req 4.2
```

**Dependencies**:
- **EventRepository**: event persistence and fingerprint lookup
- **ClusterRepository**: candidate retrieval and cluster updates
- **EmbeddingModelCache**: embedding model load and reuse
- runtime-state flag store for `semantic_ready_for_active_window`

**Data Model**:
```text
AssignmentDecision {
  cluster_id: string
  decision: "joined_existing_cluster" | "created_new_cluster"
  cluster_status: "draft" | "stable"
  semantic_score: float | null
  time_weight: float | null
  final_score: float | null
  candidate_parent_cluster_id: string | null
  candidate_parent_score: float | null
}
```

### Component: ClusterRepository
**Purpose**: Persist and query cluster state, sparse semantic centroids, projection centroids, exemplars, and merge audit data.
**Location**: `src/demo/repositories/cluster_repository.py`

**Interface**:
```text
acquire_bucket_lock(bucket_key) -> None
find_recent_candidates(embedding, vector_mode, max_reuse_age_minutes, candidate_limit, reference_time) -> list[ClusterCandidate]
join_cluster(cluster, event_id, semantic_embedding, projection_embedding, occurred_at, cluster_texts, event_text) -> Cluster
create_draft_cluster(event_id, occurred_at, semantic_embedding, projection_embedding, text, candidate_parent_cluster_id, candidate_parent_score) -> cluster_id
merge_clusters(winner, loser, evidence) -> Cluster
list_recent_draft_clusters(window_minutes) -> list[Cluster]
list_clusters_missing_semantic_embeddings(limit) -> list[cluster_id]
upsert_cluster_semantic_embedding(cluster_id, embedding) -> None

Implements: Req 1.3, Req 3.2, Req 4.3, Req 5.2, Req 8.3
```

**Dependencies**:
- PostgreSQL with pgvector

**Data Model**:
```text
Cluster {
  cluster_id: uuid
  status: "draft" | "stable"
  first_seen_at: datetime
  last_seen_at: datetime
  member_count: int
  centroid_embedding: vector | null
  projection_centroid_embedding: vector
  exemplar_event_ids: list[string]
  keywords: list[string]
  candidate_parent_cluster_id: uuid | null
  candidate_parent_score: float | null
}

MergeAudit {
  merge_id: uuid
  winner_cluster_id: uuid
  loser_cluster_id: uuid
  evidence_score: float
  evidence_summary: json
  merged_at: datetime
}
```

### Component: EventRepository
**Purpose**: Persist immutable event records, normalized fingerprints, replay metadata, and event-level embedding rows.
**Location**: [src/demo/repositories/event_repository.py](../../src/demo/repositories/event_repository.py)

**Interface**:
```text
insert_pending_event(event, normalized_text, fingerprint, semantic_embedding, projection_embedding) -> None
get_event_by_id(event_id) -> StoredEvent | null
find_recent_fingerprint(fingerprint, max_reuse_age_minutes, exclude_event_id, reference_time) -> StoredEvent | null
load_baseline_story() -> list[StoredEvent]
fetch_event_embeddings(event_ids, vector_mode) -> map[event_id, vector]
list_events_missing_semantic_embeddings(limit) -> list[StoredEvent]
upsert_event_semantic_embedding(event_id, embedding) -> None

Implements: Req 1.1, Req 2.1, Req 2.2, Req 5.1, Req 8.3
```

**Dependencies**:
- PostgreSQL

**Data Model**:
```text
StoredEvent {
  event_id: string
  source: string
  occurred_at: datetime
  ingested_at: datetime
  normalized_text: string
  fingerprint: string
  text: string
  metadata: json
  cluster_id: uuid | null
}
```

### Component: MaintenanceWorker
**Purpose**: Periodically merge recent draft clusters when stronger post-hoc evidence exists and backfill missing semantic rows after degraded-mode ingest windows.
**Location**: [src/demo/workers/maintenance.py](../../src/demo/workers/maintenance.py)

**Interface**:
```text
run_once() -> MaintenanceSummary
run_forever(interval_minutes) -> None

Implements: Req 4.1, Req 4.2, Req 4.3, Req 8.3
```

**Dependencies**:
- **ClusterRepository**
- **EventRepository**

**Data Model**:
```text
MaintenanceSummary {
  scanned_draft_clusters: int
  merges_performed: int
  skipped_due_to_weak_evidence: int
  backfilled_semantic_events: int
  backfilled_semantic_clusters: int
}
```

### Component: ReplayCLI
**Purpose**: Replay the deterministic baseline story, send live test events, and trigger resets.
**Location**: [src/demo/cli.py](../../src/demo/cli.py)

**Interface**:
```text
demo replay
demo replay --rebase-now
demo replay --story-path data/week_story_1000.jsonl --rebase-now
demo watch
demo send "text..." --source manual
demo reset
demo calibrate
demo calibrate --story-path data/week_story_1000.jsonl --labels-path data/week_story_1000.labels.json

Implements: Req 5.1, Req 5.3, Req 5.4, Req 5.5, Req 7.1, Req 7.3
```

**Dependencies**:
- **IngestionAPI**
- **ResetService**
- **ThresholdCalibrator**
- **LiveDashboard**

**Behavior Notes**:
- `demo replay --rebase-now` rebases the chosen story into the recent `draft_merge_window_minutes` so draft clusters remain eligible for the merge worker during the live walkthrough.
- rebased events preserve input order and copy the original timestamp into `metadata.original_occurred_at`.
- `--story-path` allows replaying an alternate story file, such as the 1,000-event week-long sample, without replacing the checked-in baseline story used by `demo reset`.

**Data Model**:
```text
CLICommandResult {
  command: string
  status: "ok" | "error"
  summary: string
}
```

### Component: LiveDashboard
**Purpose**: Maintain an in-memory operator view of active clusters, recent merges, and the live SSE stream without polling the database.
**Location**: [src/demo/dashboard/live_dashboard.py](../../src/demo/dashboard/live_dashboard.py)

**Interface**:
```text
watch(stream_url) -> None

Implements: Req 6.1, Req 6.2
```

**Dependencies**:
- **IngestionAPI**

**Data Model**:
```text
StreamEvent {
  type: "assignment" | "merge" | "reset" | "maintenance"
  payload: json
  emitted_at: datetime
}

ActiveClusterState {
  cluster_id: string
  status: "draft" | "stable"
  event_count: int
  last_event_id: string
  last_confidence: float
}
```

### Component: ThresholdCalibrator
**Purpose**: Run a pure domain simulation over labeled replay data and emit a calibration report without database side effects.
**Location**: [src/demo/calibration/threshold_calibrator.py](../../src/demo/calibration/threshold_calibrator.py)

**Interface**:
```text
run() -> CalibrationReport

Implements: Req 3.1, Req 7.1, Req 7.2
```

**Dependencies**:
- baseline story loader
- label loader
- **EmbeddingModelCache**

**Data Model**:
```text
CalibrationReport {
  recommended_thresholds: {
    join_threshold: float
    draft_score_min: float
    draft_score_max: float
    merge_evidence_threshold: float
  }
  search_space: list[json]
  metrics: {
    pairwise_precision: float
    pairwise_recall: float
    pairwise_f1: float
  }
  generated_at: datetime
}
```

### Component: ResetService
**Purpose**: Wipe mutable demo state and re-insert the baseline story without removing Docker volumes.
**Location**: [src/demo/services/reset_service.py](../../src/demo/services/reset_service.py)

**Interface**:
```text
ensure_baseline_story_loaded() -> int
reset_to_baseline(rehydrate_runtime=True) -> ResetSummary

Implements: Req 5.2, Req 5.3
```

**Dependencies**:
- **EventRepository**
- **ClusterRepository**

**Data Model**:
```text
ResetSummary {
  deleted_events: int
  deleted_clusters: int
  restored_baseline_events: int
  restored_runtime_events: int
  restored_runtime_clusters: int
  rehydrate_runtime: bool
  restored_at: datetime
}
```

### Component: EmbeddingModelCache
**Purpose**: Keep the local embedding model in `.cache/` and make that cache reusable across runs.
**Location**: [src/demo/embeddings/model_cache.py](../../src/demo/embeddings/model_cache.py)

**Interface**:
```text
load_model(config) -> EmbeddingModelHandle

Implements: Req 8.1, Req 8.3
```

**Dependencies**:
- local filesystem mounted into the API container

**Data Model**:
```text
EmbeddingModelHandle {
  cache_dir: string
  model_id: string
  backend: "sentence-transformers" | "stable-projection"
  vector_mode: "semantic" | "stable_projection"
  semantic_available: bool
}
```

## API Contracts

### `POST /events`
```json
{
  "event_id": "evt-1007",
  "source": "ticket",
  "occurred_at": "2026-04-25T12:00:00Z",
  "text": "Login errors are spiking in the support queue",
  "metadata": {
    "priority": "p2"
  }
}
```

Response:
```json
{
  "event_id": "evt-1007",
  "cluster_id": "clu-abc123",
  "decision": "created_new_cluster",
  "cluster_status": "draft",
  "confidence": 0.66,
  "score": {
    "semantic_score": 0.74,
    "time_weight": 0.90,
    "final_score": 0.66,
    "candidate_parent_cluster_id": "clu-prev001",
    "candidate_parent_score": 0.66
  }
}
```

### `GET /clusters/{cluster_id}`
Returns cluster metadata, recent member events, exemplar IDs, candidate parent evidence, and merge history.

### `GET /clusters?status={status}&since={timestamp}`
Returns recent clusters filtered by status and time window for operator inspection.

### `GET /events/stream`
SSE endpoint emitting:
```text
event: assignment
data: {"cluster_id":"clu-abc123","decision":"created_new_cluster","final_score":0.66}
```

## Storage Design

### Tables
```text
events(
  event_id text primary key,
  source text not null,
  occurred_at timestamptz not null,
  ingested_at timestamptz not null,
  text text not null,
  normalized_text text not null,
  fingerprint text not null,
  cluster_id uuid,
  decision text,
  confidence double precision,
  semantic_score double precision,
  time_weight double precision,
  final_score double precision,
  metadata jsonb not null default '{}'
)

clusters(
  cluster_id uuid primary key,
  status text not null,
  first_seen_at timestamptz not null,
  last_seen_at timestamptz not null,
  member_count integer not null,
  exemplar_event_ids jsonb not null,
  keywords jsonb not null,
  candidate_parent_cluster_id uuid,
  candidate_parent_score double precision
)

semantic_embeddings(
  entity_type text check in ('event', 'cluster'),
  entity_id text,
  embedding vector not null,
  updated_at timestamptz not null,
  primary key (entity_type, entity_id)
)

projection_embeddings(
  entity_type text check in ('event', 'cluster'),
  entity_id text,
  embedding vector not null,
  updated_at timestamptz not null,
  primary key (entity_type, entity_id)
)

runtime_state(
  key text primary key,
  bool_value boolean,
  updated_at timestamptz not null
)

merge_audit(
  merge_id uuid primary key,
  winner_cluster_id uuid not null,
  loser_cluster_id uuid not null,
  evidence_score double precision not null,
  evidence_summary jsonb not null,
  merged_at timestamptz not null
)
```

### Indexes
```text
events(event_id primary key)
events(fingerprint, occurred_at desc)
clusters(last_seen_at desc)
semantic_embeddings using hnsw (embedding vector_cosine_ops) where entity_type = 'cluster'
projection_embeddings using hnsw (embedding vector_cosine_ops) where entity_type = 'cluster'
```

### Embedding Persistence Rules
- Every ingested event writes a projection vector row into `projection_embeddings`.
- Semantic event rows are written only when the semantic model successfully returns a semantic vector.
- Every cluster always has a projection centroid row.
- Cluster semantic centroids are present only when every contributing event currently has semantic coverage; otherwise the semantic centroid row is left absent and the system scores that cluster through the projection path.
- The schema intentionally separates semantic and projection tables so degraded-mode ingest never pollutes semantic storage with fallback vectors.
- `runtime_state.semantic_ready_for_active_window` becomes true only when missing semantic event rows and cluster centroid rows in the active reuse window are both zero.

## Reset Script Behavior
- `demo reset` invokes **ResetService**.
- `demo replay` may invoke **ResetService** with either the baseline story or an alternate story supplied by `--story-path`.
- The reset flow runs in one transaction when possible:
  - delete or truncate mutable rows in `merge_audit`, `semantic_embeddings`, `projection_embeddings`, `events`, and `clusters`
  - preserve database schema, pgvector extension, and indexes
  - reinsert the baseline story from `baseline_story_path`
  - when `rehydrate_runtime=True`, replay the baseline story back into the live runtime tables so the operator immediately has a restored demo state
  - emit a `reset` event to the SSE stream
- The reset flow does not touch Docker volumes or `.cache/`.
- `demo replay --rebase-now` compresses the replayed story into the recent `draft_merge_window_minutes` while preserving order, so the maintenance merge path can still act on draft clusters during the demo.

## Calibration Script Behavior
- `demo calibrate` invokes **ThresholdCalibrator** over the labeled baseline story.
- `demo calibrate --story-path ... --labels-path ...` overrides the default baseline files for offline evaluation.
- Search space:
  - `join_threshold`: e.g. `0.68` to `0.80`
  - `draft_score_min`: e.g. `0.50` to `0.68`
  - `draft_score_max`: derived from the candidate `join_threshold` during calibration so the draft band stays anchored to the join boundary
  - `merge_evidence_threshold`: e.g. `0.80` to `0.92`
- Output:
  - machine-readable JSON
  - Markdown summary for interviewer review
  - recommended values written to stdout for manual config update

## Degraded-Mode Semantic Backfill
- When `EmbeddingModelCache` cannot provide semantic embeddings for an event, the online path still persists the projection vector and continues clustering through `stable_projection`.
- The missing semantic event row is left absent in `semantic_embeddings`.
- The **MaintenanceWorker** periodically revisits events without semantic rows and retries loading the semantic model before attempting semantic backfill.
- After all events in a cluster have semantic coverage, the **MaintenanceWorker** computes and persists that cluster's semantic centroid into `semantic_embeddings`.
- Only after active-window missing semantic event rows and cluster centroid rows both reach zero does the **MaintenanceWorker** set `semantic_ready_for_active_window=true`, allowing online retrieval to switch from projection to semantic.
- The design prefers sparse semantic storage plus later repair over writing fallback projection vectors into semantic columns or rows.
