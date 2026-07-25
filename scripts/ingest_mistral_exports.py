from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile
import zipfile

from dotenv import load_dotenv

from astrospace.admin.client import SupabaseAdminClient
from astrospace.knowledge.ingestion.analyzer import AutomatedChunkAnalyzer
from astrospace.knowledge.ingestion.mistral import MistralOcrExtractor
from astrospace.knowledge.ingestion.pipeline import IngestionPipeline
from astrospace.knowledge.ingestion.repository import SupabaseKnowledgeRepository


BOOKS = (
    {
        "export": "2015.406251.Brihat-Jataka_text.pdf",
        "pdf": "2015.406251.Brihat-Jataka_text.pdf",
        "source_key": "brihat-jataka",
        "title": "Brihat Jataka",
        "author": "Varahamihira",
    },
    {
        "export": "2015.92117.Mantreswaras-Phaladeepika.pdf",
        "pdf": "2015.92117.Mantreswaras-Phaladeepika.pdf",
        "source_key": "phaladeepika-mantreswara",
        "title": "Mantreswara's Phaladeepika",
        "author": "Mantreswara",
    },
    {
        "export": (
            "Brihat Parasara Hora Sastra with English Translation "
            "Girish Chand Sharma Volume 1.pdf"
        ),
        "pdf": (
            "Brihat Parasara Hora Sastra with English Translation "
            "Girish Chand Sharma Volume 1.pdf"
        ),
        "source_key": "brihat-parasara-hora-sastra-volume-1",
        "title": "Brihat Parasara Hora Sastra, Volume 1",
        "author": "Maharishi Parasara",
    },
    {
        "export": "Uttara kalamritam..pdf",
        "pdf": "Uttara kalamritam..pdf",
        "source_key": "uttara-kalamritam",
        "title": "Uttara Kalamritam",
        "author": None,
    },
    {
        "export": "saravaliofkalyan01kalyuoft.pdf",
        "pdf": "saravaliofkalyan01kalyuoft.pdf",
        "source_key": "saravali-kalyana-varma",
        "title": "Saravali",
        "author": "Kalyana Varma",
    },
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _archive_export(export_path: Path) -> bytes:
    with tempfile.NamedTemporaryFile(suffix=".zip") as handle:
        with zipfile.ZipFile(handle.name, "w", zipfile.ZIP_DEFLATED) as archive:
            for item in sorted(export_path.rglob("*")):
                if item.is_file() and item.name != ".DS_Store":
                    archive.write(item, item.relative_to(export_path))
        handle.seek(0)
        return handle.read()


def _run(
    *,
    client: SupabaseAdminClient,
    export_root: Path,
    pdf_root: Path,
    spec: dict,
) -> dict:
    export_path = export_root / spec["export"]
    pdf_path = pdf_root / spec["pdf"]
    source_key = spec["source_key"]
    pdf_storage_path = f"pdfs/{source_key}.pdf"
    export_storage_path = f"ocr/mistral/{source_key}/ocr-export.zip"
    if not export_path.is_dir():
        raise FileNotFoundError(f"Missing Mistral export: {export_path}")
    if not pdf_path.is_file():
        raise FileNotFoundError(f"Missing source PDF: {pdf_path}")

    run = client.insert("knowledge_ingestion_runs", {
        "source_key": source_key,
        "status": "running",
        "analyzer_model": "automated-mistral-quality-v1",
        "start_section": 0,
        "started_at": _now(),
    })[0]
    try:
        client.upload_source(
            "astro-knowledge-sources",
            pdf_storage_path,
            pdf_path.read_bytes(),
            "application/pdf",
        )
        client.upload_source(
            "astro-knowledge-sources",
            export_storage_path,
            _archive_export(export_path),
            "application/zip",
        )
        extractor = MistralOcrExtractor(
            source_path=pdf_path,
            title=spec["title"],
            author=spec["author"],
            export_storage_path=export_storage_path,
            exported_at="2026-07-26T00:36:31Z",
        )
        result = IngestionPipeline(
            SupabaseKnowledgeRepository(client.url, client.secret),
            analyzer=AutomatedChunkAnalyzer(),
            extractor=extractor,
            max_window_chars=16000,
            max_window_blocks=40,
            audit_sample_rate=0.02,
        ).ingest(
            export_path,
            storage_path=pdf_storage_path,
            source_key=source_key,
        )
        client.patch(
            "knowledge_ingestion_runs",
            params={"id": f"eq.{run['id']}"},
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
        client.insert("knowledge_audit_log", {
            "action": "source.mistral_ingested",
            "entity_type": "source",
            "entity_id": result["source_id"],
            "source_id": result["source_id"],
            "reason": "Imported verified Mistral OCR export with automated quality gates",
            "after_state": {
                **result,
                "ocr_export_storage_path": export_storage_path,
                "audit_sample_rate": 0.02,
            },
        })
        return result
    except Exception as exc:
        client.patch(
            "knowledge_ingestion_runs",
            params={"id": f"eq.{run['id']}"},
            payload={
                "status": "failed",
                "error_message": str(exc)[:2000],
                "completed_at": _now(),
            },
        )
        raise


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(
        description="Ingest Mistral OCR playground exports into Supabase"
    )
    parser.add_argument(
        "--knowledge-root",
        default="Astro Space Knowledge Base",
    )
    parser.add_argument("--only", action="append", default=[])
    parser.add_argument("--keep-stale-pilot", action="store_true")
    args = parser.parse_args()

    root = Path(args.knowledge_root)
    export_root = root / "ocr-playground-download-20260726T003631Z"
    pdf_root = root / "PDFs"
    client = SupabaseAdminClient()
    selected = [
        spec for spec in BOOKS
        if not args.only or spec["source_key"] in set(args.only)
    ]
    results = []
    for spec in selected:
        result = _run(
            client=client,
            export_root=export_root,
            pdf_root=pdf_root,
            spec=spec,
        )
        results.append(result)
        print(json.dumps(result, ensure_ascii=False))

    if not args.keep_stale_pilot and not args.only:
        stale = client.one("knowledge_sources", params={
            "source_key": "eq.uttara-kalamritam-pdf-pilot",
            "select": "id,source_key",
        })
        if stale:
            client.request(
                "DELETE",
                "knowledge_chunks",
                params={"source_id": f"eq.{stale['id']}"},
            )
            client.request(
                "DELETE",
                "knowledge_sections",
                params={"source_id": f"eq.{stale['id']}"},
            )
            client.patch(
                "knowledge_sources",
                params={"id": f"eq.{stale['id']}"},
                payload={
                    "status": "archived",
                    "metadata": {
                        "superseded_by_source_key": "uttara-kalamritam",
                        "retired_at": _now(),
                    },
                },
            )
            client.insert("knowledge_audit_log", {
                "action": "source.stale_pilot_removed",
                "entity_type": "source",
                "entity_id": stale["id"],
                "reason": "Archived Poppler pilot after complete Mistral OCR replacement",
                "before_state": stale,
                "after_state": {
                    "status": "archived",
                    "superseded_by_source_key": "uttara-kalamritam",
                },
            })
    print(json.dumps({"completed": len(results), "results": results}, indent=2))


if __name__ == "__main__":
    main()
