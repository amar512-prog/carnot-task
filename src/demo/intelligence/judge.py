from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Protocol
from urllib import error, request

from demo.config import DemoConfig
from demo.domain.models import JudgeDecision, RerankedCandidate


class ClusterJudge(Protocol):
    def decide(self, *, event_text: str, candidates: list[RerankedCandidate]) -> JudgeDecision:
        ...

    def generate_summary(self, *, event_text: str, metadata: dict[str, object]) -> str:
        ...


@dataclass(slots=True)
class HeuristicClusterJudge:
    config: DemoConfig

    def decide(self, *, event_text: str, candidates: list[RerankedCandidate]) -> JudgeDecision:
        if not candidates:
            return JudgeDecision(decision="none", confidence=0.0, reason="No candidate clusters survived retrieval.")

        top = candidates[0]
        if len(candidates) > 1:
            second = candidates[1]
            if (
                top.gate2_score >= self.config.merge_evidence_threshold
                and second.gate2_score >= self.config.merge_evidence_threshold
                and abs(top.gate2_score - second.gate2_score) <= 0.05
            ):
                return JudgeDecision(
                    decision="both",
                    confidence=min(top.gate2_score, second.gate2_score),
                    reason="Two top candidates have near-equal reranker scores above the merge threshold.",
                )
        if top.gate2_score >= self.config.join_threshold:
            return JudgeDecision(
                decision="cluster_a",
                confidence=top.gate2_score,
                reason="Top reranked candidate exceeds the join threshold.",
                chosen_cluster_id=top.candidate.cluster_id,
            )
        return JudgeDecision(
            decision="none",
            confidence=top.gate2_score,
            reason="No reranked candidate exceeded the join threshold.",
        )

    def generate_summary(self, *, event_text: str, metadata: dict[str, object]) -> str:
        theme = str(metadata.get("expected_cluster") or metadata.get("theme") or "").strip()
        cleaned = " ".join(event_text.strip().split())
        if theme:
            return f"{theme}: {cleaned[:220]}"
        return cleaned[:220]


@dataclass(slots=True)
class OllamaClusterJudge:
    model_id: str
    api_url: str
    timeout_seconds: int
    fallback: HeuristicClusterJudge

    def decide(self, *, event_text: str, candidates: list[RerankedCandidate]) -> JudgeDecision:
        if not candidates:
            return self.fallback.decide(event_text=event_text, candidates=candidates)
        prompt = self._decision_prompt(event_text=event_text, candidates=candidates)
        payload = self._generate_json(prompt)
        if payload is None:
            return self.fallback.decide(event_text=event_text, candidates=candidates)

        decision = str(payload.get("decision") or "").strip().lower()
        confidence = _bounded_confidence(payload.get("confidence"))
        reason = str(payload.get("reason") or "No reason supplied by judge.").strip()
        if decision not in {"cluster_a", "cluster_b", "both", "none"}:
            return self.fallback.decide(event_text=event_text, candidates=candidates)
        chosen_cluster_id = None
        if decision == "cluster_a" and candidates:
            chosen_cluster_id = candidates[0].candidate.cluster_id
        elif decision == "cluster_b" and len(candidates) > 1:
            chosen_cluster_id = candidates[1].candidate.cluster_id
        elif decision == "cluster_b":
            return self.fallback.decide(event_text=event_text, candidates=candidates)
        return JudgeDecision(
            decision=decision,
            confidence=confidence,
            reason=reason,
            chosen_cluster_id=chosen_cluster_id,
        )

    def generate_summary(self, *, event_text: str, metadata: dict[str, object]) -> str:
        prompt = self._summary_prompt(event_text=event_text, metadata=metadata)
        payload = self._generate_json(prompt)
        if payload is None:
            return self.fallback.generate_summary(event_text=event_text, metadata=metadata)
        summary_text = str(payload.get("summary_text") or "").strip()
        if not summary_text:
            return self.fallback.generate_summary(event_text=event_text, metadata=metadata)
        return " ".join(summary_text.split())[:220]

    def _generate_json(self, prompt: str) -> dict[str, object] | None:
        body = json.dumps(
            {
                "model": self.model_id,
                "prompt": prompt,
                "stream": False,
                "format": "json",
                "options": {"temperature": 0},
            }
        ).encode("utf-8")
        with open("/app/reports/ollama_log.txt", "a") as f:
            f.write(f"--- OLLAMA REQUEST ---\n{body.decode('utf-8')}\n")
        req = request.Request(
            self.api_url.rstrip("/") + "/api/generate",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=self.timeout_seconds) as response:
                outer = json.loads(response.read().decode("utf-8"))
                with open("/app/reports/ollama_log.txt", "a") as f:
                    f.write(f"--- OLLAMA RESPONSE ---\n{json.dumps(outer)}\n")
        except (OSError, error.URLError, error.HTTPError, json.JSONDecodeError) as e:
            with open("/app/reports/ollama_log.txt", "a") as f:
                f.write(f"--- OLLAMA ERROR ---\n{str(e)}\n")
            return None
        # raw = outer.get("response")
        raw = outer.get("thinking")
        if not isinstance(raw, str):
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None

    def _decision_prompt(self, *, event_text: str, candidates: list[RerankedCandidate]) -> str:
        lines = [
            "You are deciding whether a new event belongs to existing incident clusters.",
            "Return only JSON with keys: decision, confidence, reason.",
            "Allowed decisions: cluster_a, cluster_b, both, none.",
            "",
            f"Event: {event_text}",
        ]
        labels = ["A", "B"]
        for index, candidate in enumerate(candidates[:2]):
            lines.extend(
                [
                    "",
                    f"Cluster {labels[index]} ID: {candidate.candidate.cluster_id}",
                    f"Cluster {labels[index]} Summary: {candidate.candidate.summary_text}",
                    f"Cluster {labels[index]} Gate1 Score: {candidate.gate1_score:.4f}",
                    f"Cluster {labels[index]} Gate2 Score: {candidate.gate2_score:.4f}",
                ]
            )
        if len(candidates) == 1:
            lines.extend(["", "Cluster B is unavailable for this decision."])
        return "\n".join(lines)

    def _summary_prompt(self, *, event_text: str, metadata: dict[str, object]) -> str:
        expected_cluster = str(metadata.get("expected_cluster") or "").strip()
        theme = str(metadata.get("theme") or "").strip()
        return "\n".join(
            [
                "Write a short cluster summary for the incident event below.",
                "Return only JSON with key: summary_text.",
                "Use one concise sentence that is useful for future retrieval.",
                "If expected_cluster or theme is present, align the wording to that cluster theme without literally copying an ID unless it reads naturally.",
                "",
                f"Event: {event_text}",
                f"expected_cluster: {expected_cluster}",
                f"theme: {theme}",
            ]
        )


def _bounded_confidence(value: object) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, score))


def load_judge(config: DemoConfig) -> ClusterJudge:
    fallback = HeuristicClusterJudge(config=config)
    return OllamaClusterJudge(
        model_id=config.judge_model_id,
        api_url=config.judge_api_url,
        timeout_seconds=config.judge_timeout_seconds,
        fallback=fallback,
    )
