from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime
from functools import lru_cache
import json
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from demo.config import DemoConfig, load_config
from demo.domain.models import EventInput
from demo.embeddings.model_cache import EmbeddingModel, load_model
from demo.intelligence import CandidateReranker, ClusterJudge, load_judge, load_reranker
from demo.repositories.cluster_repository import ClusterRepository
from demo.repositories.database import connect_db, wait_for_db
from demo.repositories.event_repository import EventRepository
from demo.services.clustering_service import ClusteringService
from demo.services.reset_service import ResetService


class EventRequest(BaseModel):
    event_id: str
    source: str
    occurred_at: datetime
    text: str
    metadata: dict[str, Any] = Field(default_factory=dict)


@lru_cache(maxsize=1)
def get_config() -> DemoConfig:
    return load_config()


@lru_cache(maxsize=1)
def get_model() -> EmbeddingModel:
    return load_model(get_config())


@lru_cache(maxsize=1)
def get_reranker() -> CandidateReranker:
    return load_reranker(get_config())


@lru_cache(maxsize=1)
def get_judge() -> ClusterJudge:
    return load_judge(get_config())


@asynccontextmanager
async def lifespan(_: FastAPI):
    wait_for_db()
    ResetService(get_config()).ensure_baseline_story_loaded()
    get_model()
    get_reranker()
    get_judge()
    yield


app = FastAPI(title="Recent-Event Clustering Demo", lifespan=lifespan)


def _service() -> ClusteringService:
    return ClusteringService(
        config=get_config(),
        model=get_model(),
        reranker=get_reranker(),
        judge=get_judge(),
    )


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/events")
def ingest_event(request: EventRequest):
    event = EventInput(
        event_id=request.event_id,
        source=request.source,
        occurred_at=request.occurred_at,
        text=request.text,
        metadata=request.metadata,
    )
    with connect_db() as conn:
        result = _service().assign_event(conn, event)
        conn.commit()
    return {
        "event_id": request.event_id,
        "cluster_id": result.cluster_id,
        "decision": result.decision,
        "cluster_status": result.cluster_status,
        "confidence": result.confidence,
        "score": {
            "gate1_score": result.gate1_score,
            "gate2_score": result.gate2_score,
            "judge_confidence": result.judge_confidence,
            "judge_decision": result.judge_decision,
            "semantic_score": result.semantic_score,
            "time_weight": result.time_weight,
            "final_score": result.final_score,
            "candidate_parent_cluster_id": result.candidate_parent_cluster_id,
            "candidate_parent_score": result.candidate_parent_score,
        },
    }


@app.get("/clusters/{cluster_id}")
def get_cluster(cluster_id: str):
    with connect_db() as conn:
        cluster = ClusterRepository(conn).get_cluster_details(cluster_id)
    if cluster is None:
        raise HTTPException(status_code=404, detail="Cluster not found")
    return cluster


@app.get("/clusters")
def list_clusters(
    status: str | None = Query(default=None),
    since: datetime | None = Query(default=None),
):
    with connect_db() as conn:
        clusters = ClusterRepository(conn).list_clusters(status=status, since=since)
    return {"items": clusters}


async def _stream_generator():
    last_id = 0
    while True:
        with connect_db() as conn:
            rows = EventRepository(conn).fetch_stream_events(last_id)
        if rows:
            for row in rows:
                last_id = int(row["stream_id"])
                yield f"event: {row['event_type']}\n"
                yield f"data: {json.dumps(row['payload'])}\n\n"
        else:
            yield "event: heartbeat\n"
            yield "data: {}\n\n"
        await asyncio.sleep(1)


@app.get("/events/stream")
async def event_stream():
    return StreamingResponse(_stream_generator(), media_type="text/event-stream")
