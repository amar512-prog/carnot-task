# Calibration Playbook

## Purpose
`ThresholdCalibrator` exists so the demo can justify its thresholds from the same labeled replay data used in the interview story. The output is not an opaque magic number; it is a report showing what threshold combinations were tested and which set performed best.

## Command
```bash
docker compose exec api demo calibrate
```

Alternative labeled samples can be supplied directly:

```bash
docker compose exec api demo calibrate --story-path data/week_story_1000.jsonl --labels-path data/week_story_1000.labels.json
```

## Inputs
- Baseline labeled event data from `data/baseline_story.labels.json`
- Default config from `config/demo.yaml`
- Active vector path resolved from `embedding_backend` plus `vector_mode`

If `--story-path` or `--labels-path` is provided, the calibrator uses those files instead of the baseline paths from config.

The calibrator is a pure simulator. It does not touch PostgreSQL, and it follows the same runtime rule as the online system:
- projection vectors are always available
- semantic vectors may be missing
- when semantic vectors are missing, scoring falls back to the projection path without fabricating semantic rows

## What Gets Swept
- `join_threshold`
- `draft_score_min`
- `merge_evidence_threshold`
- derived `draft_score_max` tied to each candidate `join_threshold`

Typical sweep strategy:

```text
join_threshold: 0.68 -> 0.80
draft_score_min: 0.50 -> 0.68
draft_score_max: derived from each candidate join_threshold
merge_evidence_threshold: 0.80 -> 0.92
```

## Evaluation Logic
For each threshold set:
1. Replay the labeled story in deterministic order.
2. Record online decisions and background merges.
3. Compare resulting cluster memberships to the expected labels.
4. Compute pairwise clustering metrics such as precision, recall, and F1.
5. Keep the best-performing threshold set, breaking ties toward the more conservative online configuration.

## Outputs
- Markdown summary for human review
- JSON report for machine inspection
- Recommended threshold block that can be copied into `config/demo.yaml`

## How to Interpret the Results
- Higher `join_threshold` usually means fewer false joins but more `draft` clusters.
- Lower `draft_score_min` makes the system more willing to treat weak evidence as draft-worthy instead of clearly new.
- Higher `merge_evidence_threshold` makes background merges rarer but safer.

The best demo setting is the one that tells a coherent story:
- online path is conservative
- draft band captures uncertainty
- merge path resolves uncertainty only with stronger evidence
- the same threshold story still holds if the system pivots to stable-projection mode while semantic backfill catches up later

## Expected Interview Talking Point
If asked why the thresholds are not arbitrary, point to the calibration report and say:

> We tuned the online join threshold, the draft band, and the merge-evidence threshold against the same labeled story data used in the walkthrough, so the defaults are reproducible rather than hand-waved.
