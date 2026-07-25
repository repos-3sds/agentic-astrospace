from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from functools import lru_cache

import psycopg
import requests

from ..knowledge.ingestion.embeddings import FeatureHashEmbedder


@dataclass(frozen=True)
class SourcePassage:
    chunk_id: str
    source_key: str
    book: str
    edition: str | None
    title: str | None
    content: str
    page_labels: tuple[str, ...]
    domains: tuple[str, ...]
    topics: tuple[str, ...]
    lexical_score: float
    semantic_score: float

    def to_dict(self) -> dict:
        return asdict(self)


class NullSourceRetriever:
    def retrieve(self, query: str, domains: list[str], limit: int = 8) -> list[SourcePassage]:
        return []


class PostgresSourceRetriever:
    def __init__(self, database_url: str, embedder: FeatureHashEmbedder | None = None):
        self.database_url = database_url.replace(
            "postgresql+psycopg://", "postgresql://", 1,
        )
        self.embedder = embedder or FeatureHashEmbedder()

    def retrieve(self, query: str, domains: list[str], limit: int = 8) -> list[SourcePassage]:
        embedding = "[" + ",".join(
            f"{value:.9f}" for value in self.embedder.embed(query)
        ) + "]"
        with psycopg.connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute("""
                    select
                      c.id, s.source_key, s.title, s.edition, c.title, c.content,
                      c.page_labels, c.domains, c.topics,
                      ts_rank_cd(c.search_vector, websearch_to_tsquery('english', %s))::real,
                      (1 - (c.embedding <=> %s::extensions.vector))::real
                    from public.knowledge_chunks c
                    join public.knowledge_sources s on s.id = c.source_id
                    where c.quality_status = 'published'
                      and (
                        %s::text[] is null
                        or cardinality(c.domains) = 0
                        or c.domains && %s::text[]
                      )
                    order by (
                      ts_rank_cd(c.search_vector, websearch_to_tsquery('english', %s)) * 0.55
                      + (1 - (c.embedding <=> %s::extensions.vector)) * 0.45
                    ) desc
                    limit %s
                """, (query, embedding, domains or None, domains or None,
                      query, embedding, min(max(limit, 1), 20)))
                rows = cursor.fetchall()
        return [
            SourcePassage(
                chunk_id=str(row[0]),
                source_key=row[1],
                book=row[2],
                edition=row[3],
                title=row[4],
                content=row[5],
                page_labels=tuple(row[6] or []),
                domains=tuple(row[7] or []),
                topics=tuple(row[8] or []),
                lexical_score=float(row[9] or 0),
                semantic_score=float(row[10] or 0),
            )
            for row in rows
        ]


class SupabaseSourceRetriever:
    def __init__(self, url: str, service_key: str,
                 embedder: FeatureHashEmbedder | None = None):
        self.base_url = f"{url.rstrip('/')}/rest/v1"
        self.headers = {
            "apikey": service_key,
            "Authorization": f"Bearer {service_key}",
            "Content-Type": "application/json",
        }
        self.embedder = embedder or FeatureHashEmbedder()

    def retrieve(self, query: str, domains: list[str], limit: int = 8) -> list[SourcePassage]:
        embedding = "[" + ",".join(
            f"{value:.9f}" for value in self.embedder.embed(query)
        ) + "]"
        response = requests.post(
            f"{self.base_url}/rpc/search_knowledge_chunks",
            headers=self.headers,
            json={
                "query_text": query,
                "query_embedding": embedding,
                "filter_domains": domains or None,
                "result_limit": min(max(limit, 1), 20),
            },
            timeout=30,
        )
        response.raise_for_status()
        rows = response.json()
        source_ids = sorted({row["source_id"] for row in rows})
        sources = {}
        if source_ids:
            source_response = requests.get(
                f"{self.base_url}/knowledge_sources",
                headers=self.headers,
                params={
                    "id": f"in.({','.join(source_ids)})",
                    "select": "id,source_key,title,edition",
                },
                timeout=30,
            )
            source_response.raise_for_status()
            sources = {row["id"]: row for row in source_response.json()}
        return [
            SourcePassage(
                chunk_id=row["id"],
                source_key=sources.get(row["source_id"], {}).get("source_key", ""),
                book=sources.get(row["source_id"], {}).get("title", ""),
                edition=sources.get(row["source_id"], {}).get("edition"),
                title=row.get("title"),
                content=row["content"],
                page_labels=tuple(row.get("page_labels") or []),
                domains=tuple(row.get("domains") or []),
                topics=tuple(row.get("topics") or []),
                lexical_score=float(row.get("lexical_score") or 0),
                semantic_score=float(row.get("semantic_score") or 0),
            )
            for row in rows
        ]


@lru_cache(maxsize=1)
def get_source_retriever():
    service_key = (
        os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        or os.getenv("SUPABASE_SECRET_KEY")
    )
    if os.getenv("SUPABASE_URL") and service_key:
        return SupabaseSourceRetriever(os.environ["SUPABASE_URL"], service_key)
    url = os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_URL") or ""
    if not url.startswith(("postgresql://", "postgresql+psycopg://")):
        return NullSourceRetriever()
    return PostgresSourceRetriever(url)
