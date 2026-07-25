from __future__ import annotations

import json
import os
from typing import Protocol

import psycopg
import requests

from .models import EpubBook, KnowledgeChunk


class KnowledgeRepository(Protocol):
    def replace(self, book: EpubBook, chunks: list[KnowledgeChunk], *,
                storage_bucket: str, storage_path: str, parser_version: str) -> str: ...


def _postgres_url(url: str) -> str:
    return url.replace("postgresql+psycopg://", "postgresql://", 1)


def _vector(values: tuple[float, ...] | None) -> str | None:
    if values is None:
        return None
    return "[" + ",".join(f"{value:.9f}" for value in values) + "]"


class PostgresKnowledgeRepository:
    def __init__(self, database_url: str | None = None):
        url = database_url or os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_URL")
        if not url or not url.startswith(("postgresql://", "postgresql+psycopg://")):
            raise RuntimeError("A PostgreSQL DATABASE_URL is required for knowledge ingestion")
        self.database_url = _postgres_url(url)

    def replace(self, book: EpubBook, chunks: list[KnowledgeChunk], *,
                storage_bucket: str, storage_path: str, parser_version: str) -> str:
        status = "ready" if any(c.quality_status == "published" for c in chunks) else "needs_review"
        with psycopg.connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute("""
                    insert into public.knowledge_sources (
                      source_key, title, author, language, file_type,
                      storage_bucket, storage_path, sha256, parser_version, status, metadata
                    )
                    values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                    on conflict (source_key) do update set
                      title = excluded.title,
                      author = excluded.author,
                      language = excluded.language,
                      file_type = excluded.file_type,
                      storage_bucket = excluded.storage_bucket,
                      storage_path = excluded.storage_path,
                      sha256 = excluded.sha256,
                      parser_version = excluded.parser_version,
                      status = excluded.status,
                      metadata = excluded.metadata,
                      updated_at = now()
                    returning id
                """, (
                    book.source_key, book.title, book.author, book.language,
                    book.file_type,
                    storage_bucket, storage_path, book.sha256, parser_version,
                    status, json.dumps({
                        "identifier": book.identifier,
                        **book.metadata,
                    }),
                ))
                source_id = str(cursor.fetchone()[0])
                cursor.execute("delete from public.knowledge_sections where source_id = %s", (source_id,))
                for section in book.sections:
                    cursor.execute("""
                        insert into public.knowledge_sections (
                          source_id, ordinal, href, title, page_label, exact_text,
                          text_sha256, raw_xhtml_sha256, extraction_confidence,
                          page_image_path, page_image_sha256, extraction_method,
                          metadata
                        ) values (
                          %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                          %s::jsonb
                        )
                    """, (
                        source_id, section.ordinal, section.href, section.title,
                        section.page_label, section.exact_text, section.text_sha256,
                        section.raw_xhtml_sha256, section.extraction_confidence,
                        section.page_image_path, section.page_image_sha256,
                        section.extraction_method,
                        json.dumps(section.metadata),
                    ))
                for chunk in chunks:
                    cursor.execute("""
                        insert into public.knowledge_chunks (
                          source_id, ordinal, title, content, content_sha256,
                          start_block_id, end_block_id, section_ordinals, page_labels,
                          domains, subdomains, topics, content_types, source_domains,
                          classification_confidence, extraction_confidence,
                          quality_status, quality_notes, embedding, embedding_provider,
                          retrieval_scope, retrieval_exclusion_reason,
                          scope_confidence, scope_classifier
                        ) values (
                          %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                          %s, %s, %s, %s, %s, %s::extensions.vector, %s,
                          %s, %s, %s, %s
                        )
                    """, (
                        source_id, chunk.ordinal, chunk.title, chunk.content,
                        chunk.content_sha256, chunk.start_block_id, chunk.end_block_id,
                        list(chunk.section_ordinals), list(chunk.page_labels),
                        list(chunk.domains), list(chunk.subdomains), list(chunk.topics),
                        list(chunk.content_types), list(chunk.source_domains),
                        chunk.classification_confidence,
                        chunk.extraction_confidence, chunk.quality_status,
                        list(chunk.quality_notes), _vector(chunk.embedding),
                        chunk.embedding_provider,
                        chunk.retrieval_scope,
                        chunk.retrieval_exclusion_reason,
                        chunk.scope_confidence,
                        chunk.scope_classifier,
                    ))
            connection.commit()
        return source_id


class SupabaseKnowledgeRepository:
    """Backend-only repository using Supabase's service REST API."""

    def __init__(self, url: str | None = None, service_key: str | None = None):
        self.url = (url or os.getenv("SUPABASE_URL") or "").rstrip("/")
        self.service_key = (
            service_key
            or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
            or os.getenv("SUPABASE_SECRET_KEY")
            or ""
        )
        if not self.url or not self.service_key:
            raise RuntimeError("SUPABASE_URL and a Supabase backend secret are required")
        self.base_url = f"{self.url}/rest/v1"
        self.headers = {
            "apikey": self.service_key,
            "Authorization": f"Bearer {self.service_key}",
            "Content-Type": "application/json",
        }

    def _request(self, method: str, path: str, **kwargs):
        response = requests.request(
            method, f"{self.base_url}/{path}", headers=self.headers,
            timeout=60, **kwargs,
        )
        response.raise_for_status()
        return response

    def replace(self, book: EpubBook, chunks: list[KnowledgeChunk], *,
                storage_bucket: str, storage_path: str, parser_version: str) -> str:
        final_status = (
            "ready" if any(c.quality_status == "published" for c in chunks)
            else "needs_review"
        )
        source = {
            "source_key": book.source_key,
            "title": book.title,
            "author": book.author,
            "language": book.language,
            "file_type": book.file_type,
            "storage_bucket": storage_bucket,
            "storage_path": storage_path,
            "sha256": book.sha256,
            "parser_version": parser_version,
            "status": "processing",
            "metadata": {
                "identifier": book.identifier,
                **book.metadata,
            },
        }
        headers = {**self.headers, "Prefer": "resolution=merge-duplicates,return=representation"}
        response = requests.post(
            f"{self.base_url}/knowledge_sources",
            headers=headers,
            params={"on_conflict": "source_key"},
            json=source,
            timeout=60,
        )
        response.raise_for_status()
        source_id = response.json()[0]["id"]
        try:
            params = {"source_id": f"eq.{source_id}"}
            self._request("DELETE", "knowledge_chunks", params=params)
            self._request("DELETE", "knowledge_sections", params=params)
            for section in book.sections:
                if section.page_image and section.page_image_path:
                    self._upload_asset(
                        storage_bucket,
                        section.page_image_path,
                        section.page_image,
                        "image/jpeg",
                    )
            sections = [{
                "source_id": source_id,
                "ordinal": section.ordinal,
                "href": section.href,
                "title": section.title,
                "page_label": section.page_label,
                "exact_text": section.exact_text,
                "text_sha256": section.text_sha256,
                "raw_xhtml_sha256": section.raw_xhtml_sha256,
                "extraction_confidence": section.extraction_confidence,
                "page_image_path": section.page_image_path,
                "page_image_sha256": section.page_image_sha256,
                "extraction_method": section.extraction_method,
                "metadata": section.metadata,
            } for section in book.sections]
            chunk_rows = [{
                "source_id": source_id,
                "ordinal": chunk.ordinal,
                "title": chunk.title,
                "content": chunk.content,
                "content_sha256": chunk.content_sha256,
                "start_block_id": chunk.start_block_id,
                "end_block_id": chunk.end_block_id,
                "section_ordinals": list(chunk.section_ordinals),
                "page_labels": list(chunk.page_labels),
                "domains": list(chunk.domains),
                "subdomains": list(chunk.subdomains),
                "topics": list(chunk.topics),
                "content_types": list(chunk.content_types),
                "source_domains": list(chunk.source_domains),
                "classification_confidence": chunk.classification_confidence,
                "extraction_confidence": chunk.extraction_confidence,
                "quality_status": chunk.quality_status,
                "quality_notes": list(chunk.quality_notes),
                "embedding": _vector(chunk.embedding),
                "embedding_provider": chunk.embedding_provider,
                "retrieval_scope": chunk.retrieval_scope,
                "retrieval_exclusion_reason": chunk.retrieval_exclusion_reason,
                "scope_confidence": chunk.scope_confidence,
                "scope_classifier": chunk.scope_classifier,
            } for chunk in chunks]
            self._insert_batches("knowledge_sections", sections)
            self._insert_batches("knowledge_chunks", chunk_rows)
            self._set_status(source_id, final_status)
        except Exception:
            self._set_status(source_id, "failed")
            raise
        return source_id

    def _insert_batches(self, table: str, rows: list[dict], size: int = 100):
        for offset in range(0, len(rows), size):
            self._request("POST", table, json=rows[offset:offset + size])

    def _set_status(self, source_id: str, status: str):
        self._request(
            "PATCH", "knowledge_sources",
            params={"id": f"eq.{source_id}"},
            json={"status": status},
        )

    def _upload_asset(
        self,
        bucket: str,
        path: str,
        payload: bytes,
        content_type: str,
    ) -> None:
        response = requests.post(
            f"{self.url}/storage/v1/object/{bucket}/{path}",
            headers={
                "apikey": self.service_key,
                "Authorization": f"Bearer {self.service_key}",
                "Content-Type": content_type,
                "x-upsert": "true",
            },
            data=payload,
            timeout=120,
        )
        response.raise_for_status()


def get_knowledge_repository() -> KnowledgeRepository:
    service_key = (
        os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        or os.getenv("SUPABASE_SECRET_KEY")
    )
    if os.getenv("SUPABASE_URL") and service_key:
        return SupabaseKnowledgeRepository(service_key=service_key)
    return PostgresKnowledgeRepository()
