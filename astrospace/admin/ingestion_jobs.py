from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from .client import SupabaseAdminClient
from ..knowledge.ingestion.pipeline import IngestionPipeline
from ..knowledge.ingestion.repository import SupabaseKnowledgeRepository


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_ingestion_job(
    *,
    client: SupabaseAdminClient,
    run_id: str,
    local_path: str,
    storage_path: str,
    source_key: str,
    start_section: int,
    max_sections: int | None,
):
    path = Path(local_path)
    client.patch(
        "knowledge_ingestion_runs",
        params={"id": f"eq.{run_id}"},
        payload={"status": "running", "started_at": _now()},
    )
    try:
        result = IngestionPipeline(
            SupabaseKnowledgeRepository(client.url, client.secret),
        ).ingest(
            path,
            storage_path=storage_path,
            source_key=source_key,
            start_section=start_section,
            max_sections=max_sections,
        )
        client.patch(
            "knowledge_ingestion_runs",
            params={"id": f"eq.{run_id}"},
            payload={
                "source_id": result["source_id"],
                "status": "completed",
                "sections_count": result["sections"],
                "chunks_count": result["chunks"],
                "published_count": result["published"],
                "review_count": result["needs_review"],
                "completed_at": _now(),
            },
        )
    except Exception as exc:
        client.patch(
            "knowledge_ingestion_runs",
            params={"id": f"eq.{run_id}"},
            payload={
                "status": "failed",
                "error_message": str(exc)[:2000],
                "completed_at": _now(),
            },
        )
    finally:
        path.unlink(missing_ok=True)
