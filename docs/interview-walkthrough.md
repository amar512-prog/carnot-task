# Interview Walkthrough

## Goal
Present the system in 5 to 10 minutes as a packaged, explainable demo rather than just a whiteboard architecture.

## Suggested Order
1. **Problem framing**
   - We continuously ingest text events.
   - We detect whether a similar event happened recently.
   - If yes, we group it into a cluster.
   - If no, we create a new cluster.

2. **Show the packaged demo**
   - `docker compose up --build`
   - open `/docs`
   - run `demo watch`
   - point out that the dashboard shows active clusters, recent merges, and the raw event stream side by side

3. **Show the deterministic replay**
   - run `demo replay`
   - point out exact-dedupe joins, semantic joins, and draft-band outcomes
   - mention that every event always stores a deterministic stable-projection vector, and stores a semantic vector separately when the model is available

4. **Explain the core score**
   - `S_final = S_semantic * e^(-lambda * delta_t)`
   - freshness matters, but not as a hard cliff

5. **Explain the conservative online path**
   - exact fingerprint match joins immediately
   - otherwise recent semantic candidates are scored
   - `0.60-0.70` is the uncertainty band, so those become `draft` clusters

6. **Explain why later merges are not contradictions**
   - online path says "not enough evidence yet"
   - merge path says "we now have stronger cluster-level evidence"
   - merge worker cannot merge only because a prior score was near threshold

7. **Show repeatability**
   - run `demo reset`
   - point out that the live baseline story is restored immediately
   - rerun `demo replay` only if you want to re-stream the clustering decisions from scratch
   - mention `.cache/` keeps the sentence-transformers model warm while DB state resets cleanly
   - if asked about degraded mode, point to `vector_mode=stable_projection` as the explicit pivot switch and explain that semantic rows are backfilled later instead of being polluted by projection fallback

## Key Architecture Talking Points
- **Why FastAPI**: automatic docs make the demo inspectable.
- **Why Postgres + pgvector**: one-store baseline keeps the demo easy to run locally.
- **Why advisory locks**: prevent duplicate cluster creation when similar events arrive concurrently.
- **Why SSE**: unidirectional live updates are enough for the terminal dashboard.
- **Why calibration**: thresholds come from labeled replay data, not guesswork.
- **Why two vector representations**: semantic vectors maximize demo quality, while stable-projection vectors preserve an operational fallback when the model is unavailable.
- **Why separate embedding tables**: projection vectors are always stored, semantic vectors stay absent during outage windows, and the background worker backfills them later so semantic storage keeps its meaning.

## Questions to Expect
- **Why not a hard 1-hour window?**
  - Because a strict cliff fragments otherwise similar events at minute 61.
- **Why not merge immediately if a score is close?**
  - Because near-threshold evidence is exactly where we want to preserve uncertainty.
- **Why not use a dedicated vector DB?**
  - For the demo, Postgres + pgvector keeps the artifact simpler. The design leaves room to split that layer later.
- **How do you rerun it cleanly?**
  - `demo reset` wipes mutable DB state and restores the baseline story without removing volumes.

## Closing Summary
The demo is intentionally small but principled:
- a conservative online decision path
- a stronger-evidence background correction path
- reproducible replay and reset
- explicit threshold calibration
- a package an interviewer can actually run
