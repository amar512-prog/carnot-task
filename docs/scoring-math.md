# Scoring Math

## Core Idea
The demo uses a recency-adjusted semantic score:

```text
S_final = S_semantic * e^(-lambda * delta_t)
```

- `S_semantic` is the embedding-based similarity between the new event and the best cluster representation.
- `delta_t` is the cluster age gap in minutes, measured from the candidate cluster's `last_seen_at`.
- `lambda` controls how quickly old evidence decays.

In the default demo path, `S_semantic` comes from the sentence-transformers vector stored in `semantic_embeddings`. In degraded mode, the same formula is applied to the deterministic stable-projection vector stored in `projection_embeddings`, which is a sparse bag-of-words projection designed to preserve overlap-driven cosine similarity better than an avalanche-style cryptographic hash.

This formula keeps the online decision smooth. A highly similar event can still join a cluster after 61 minutes, but a weak similarity score fades quickly as the cluster gets older.

## Why Exponential Decay
Exponential decay avoids the hard cliff of a fixed 1-hour cutoff. Instead of saying "everything after 60 minutes is impossible," the score gradually drops as the time gap grows. That gives the system a principled way to prefer fresher evidence while still allowing near-continuations to stay together.

## Half-Life Interpretation
The config uses a half-life because it is easier to explain than raw `lambda`.

```text
lambda = ln(2) / half_life_minutes
```

If the half-life is `60` minutes:

```text
lambda = ln(2) / 60 ≈ 0.01155
```

That means every additional 60 minutes cuts the time weight in half.

## Worked Examples
Assume:
- `half_life_minutes = 60`
- `join_threshold = 0.70`
- `draft_score_min = 0.60`
- `draft_score_max = 0.70`

### Example 1: Strong match, still recent
- `S_semantic = 0.88`
- `delta_t = 15`
- `time_weight = e^(-ln(2) * 15 / 60) ≈ 0.84`
- `S_final = 0.88 * 0.84 ≈ 0.74`

Result: the event joins the existing cluster because `0.74 >= 0.70`.

### Example 2: Near-threshold draft
- `S_semantic = 0.78`
- `delta_t = 20`
- `time_weight ≈ 0.79`
- `S_final ≈ 0.62`

Result: the event creates a new `draft` cluster because the score falls inside the configured `0.60-0.70` draft band.

### Example 3: Too old to reuse confidently
- `S_semantic = 0.80`
- `delta_t = 90`
- `time_weight = e^(-ln(2) * 90 / 60) ≈ 0.35`
- `S_final ≈ 0.28`

Result: the event creates a new cluster because the old cluster is no longer recent enough to support reuse.

## Why the Merge Worker Is Not a Contradiction
The online path uses the event-to-cluster score to make a fast conservative choice. If a score lands in the draft band, the system records the best rejected candidate but does not force the join.

The **MaintenanceWorker** is allowed to merge later only when it has stronger cluster-to-cluster evidence than the original rejected event-to-cluster score. In other words:

- online path: "not enough evidence yet"
- merge path: "newer and stronger evidence has now appeared"

That is why a `0.66` draft decision is not contradicted by a later merge. The later merge is justified only if the combined cluster evidence clears the separate `merge_evidence_threshold` and beats the original rejected score.

## Why the Fallback Does Not Pollute Semantic Storage
The demo intentionally keeps projection and semantic vectors in separate tables.

- `projection_embeddings` is always populated at ingest time.
- `semantic_embeddings` is populated only when the semantic model is available.
- If the semantic model is unavailable, the system uses the projection vector for scoring but leaves the semantic entry absent.
- The **MaintenanceWorker** later backfills missing semantic rows when semantic embedding is available again.

That keeps the meaning of the semantic table clean: if a semantic row exists, it came from the semantic model, not from degraded-mode substitution.
