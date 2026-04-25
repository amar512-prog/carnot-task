# Implementation Plan

## Phase 1: Foundation
- [ ] 1. Establish the demo spec, storage, and shared configuration foundation
  - [ ] 1.1 Create the project skeleton for API, repositories, worker, CLI, and dashboard modules
  - [ ] 1.2 Add `config/demo.yaml` with threshold, replay, cache, and vector-mode settings
  - [ ] 1.3 Define event, cluster, and merge-audit schemas plus indexes, including separate `semantic_embeddings` and `projection_embeddings` tables so degraded mode never pollutes semantic storage
  - [ ] 1.4 Wire config loading into all runtime entrypoints
  - _Requirements: 1.1, 1.2, 2.2, 3.1, 8.1, 8.3_

## Phase 2: Online Clustering Path
- [ ] 2. Implement the online ingest and assignment flow
  - [ ] 2.1 Add `POST /events` with validation and structured responses
  - [ ] 2.2 Add event idempotency and normalized fingerprint lookup
  - [ ] 2.3 Acquire bucket-scoped advisory locks before join-or-create decisions
  - [ ] 2.4 Query recent vector candidates, apply recency decay, and return join or create-draft decisions
  - [ ] 2.5 Persist candidate parent evidence for draft-band outcomes
  - [ ] 2.6 Support `vector_mode` pivoting between semantic and stable-projection retrieval/scoring paths
  - [ ] 2.7 Respect the shared `semantic_ready_for_active_window` flag so online retrieval stays on projection until active-window semantic coverage is complete
  - _Requirements: 1.3, 2.1, 3.2, 3.3, 8.3, 8.4_

## Phase 3: Background Merge Correction
- [ ] 3. Implement the stronger-evidence draft merge workflow
  - [ ] 3.1 Scan recent draft clusters on a fixed interval
  - [ ] 3.2 Compare centroid and exemplar evidence against merge thresholds
  - [ ] 3.3 Prevent merges that rely only on previously rejected near-threshold evidence
  - [ ] 3.4 Persist merge audit records and updated cluster history
  - [ ] 3.5 Backfill missing semantic event rows and cluster centroids after degraded-mode ingest windows
  - [ ] 3.6 Flip the shared `semantic_ready_for_active_window` flag only after active-window semantic backfill reaches zero missing rows
  - _Requirements: 4.1, 4.2, 4.3, 8.3, 8.4_

## Phase 4: Replay, Reset, and Dashboard Flows
- [ ] 4. Implement the repeatable demo operator experience
  - [ ] 4.1 Build `demo replay` over the deterministic baseline story, with `--rebase-now` and optional `--story-path` support
  - [ ] 4.2 Build `demo reset` to wipe mutable state and restore the baseline story
  - [ ] 4.3 Add the SSE stream and terminal dashboard rendering
  - [ ] 4.4 Add interactive API docs and cluster inspection endpoints
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 6.1, 6.2, 6.3_

## Phase 5: Threshold Calibration
- [ ] 5. Implement the labeled replay calibration workflow
  - [ ] 5.1 Add threshold sweep support for join threshold, draft-band lower bound, and merge threshold, with `draft_score_max` derived from each candidate join threshold
  - [ ] 5.2 Allow `demo calibrate` to target alternate `--story-path` and `--labels-path` inputs
  - [ ] 5.3 Compute calibration metrics and select a recommended configuration
  - [ ] 5.4 Emit machine-readable and Markdown calibration reports
  - _Requirements: 7.1, 7.2, 7.3_

## Phase 6: Docs and Packaging Polish
- [ ] 6. Finish the distributable demo documentation and cache behavior
  - [ ] 6.1 Document `.cache/` usage, gitignore behavior, and first-run model warmup
  - [ ] 6.2 Write the demo runbook, scoring math note, calibration guide, and interview walkthrough, including degraded-mode behavior, sparse semantic storage, semantic backfill, the shared readiness gate, and rebased replay guidance
  - [ ] 6.3 Add a larger deterministic week-long labeled sample for replay and calibration smoke tests
  - [ ] 6.4 Add Docker Compose packaging and final demo instructions
  - _Requirements: 8.2, 8.3, 8.4_
