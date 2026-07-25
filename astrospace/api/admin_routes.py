from __future__ import annotations

from collections import Counter
from pathlib import Path
import re
import tempfile
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field

from ..admin.client import AdminStorageError, get_admin_client
from ..admin.ingestion_jobs import run_ingestion_job
from ..admin.security import AdminUser, FullAdminUser
from ..context.source_retriever import SupabaseSourceRetriever
from ..context.taxonomy import taxonomy, taxonomy_version

router = APIRouter(prefix="/api/v1/admin", tags=["knowledge-admin"])


class ReviewPayload(BaseModel):
    action: Literal["publish", "reject", "requeue"]
    reason: str = Field(min_length=3, max_length=1000)


class BulkReviewPayload(ReviewPayload):
    chunk_ids: list[str] = Field(min_length=1, max_length=100)


class ChunkMetadataPayload(BaseModel):
    title: str | None = Field(default=None, max_length=180)
    domains: list[str] | None = None
    subdomains: list[str] | None = None
    topics: list[str] | None = None
    content_types: list[str] | None = None
    source_domains: list[str] | None = None
    retrieval_scope: Literal[
        "core",
        "editorial",
        "navigation",
        "publishing",
        "devotional",
        "out_of_domain",
    ] | None = None
    retrieval_exclusion_reason: str | None = Field(default=None, max_length=300)
    reason: str = Field(min_length=3, max_length=1000)


class SourceMetadataPayload(BaseModel):
    title: str | None = Field(default=None, max_length=300)
    author: str | None = Field(default=None, max_length=300)
    edition: str | None = Field(default=None, max_length=300)
    language: str | None = Field(default=None, max_length=30)
    reason: str = Field(min_length=3, max_length=1000)


class RetrievalTestPayload(BaseModel):
    query: str = Field(min_length=2, max_length=2000)
    domains: list[str] = Field(default_factory=list)
    limit: int = Field(default=8, ge=1, le=20)


class AccessPayload(BaseModel):
    role: Literal["admin", "reviewer"]
    active: bool = True
    reason: str = Field(min_length=3, max_length=1000)


class UserStatusPayload(BaseModel):
    action: Literal["suspend", "restore"]
    reason: str = Field(min_length=3, max_length=1000)


def _client():
    try:
        return get_admin_client()
    except AdminStorageError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def _safe(call):
    try:
        return call()
    except AdminStorageError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


def _source_map(client, source_ids: set[str]) -> dict[str, dict]:
    if not source_ids:
        return {}
    rows = client.rows("knowledge_sources", params={
        "id": f"in.({','.join(sorted(source_ids))})",
        "select": "id,source_key,title,author,edition,status",
    })
    return {row["id"]: row for row in rows}


def _refresh_source_status(client, source_id: str):
    rows = client.rows("knowledge_chunks", params={
        "source_id": f"eq.{source_id}",
        "select": "quality_status",
    })
    statuses = Counter(row["quality_status"] for row in rows)
    status = "ready" if statuses["published"] else "needs_review"
    client.patch(
        "knowledge_sources", params={"id": f"eq.{source_id}"},
        payload={"status": status},
    )


@router.get("/me")
def admin_me(user: AdminUser):
    return {"id": user.id, "email": user.email, "role": user.role}


@router.get("/overview")
def overview(user: AdminUser):
    client = _client()

    def load():
        auth_users = client.auth_users()
        sources = client.rows("knowledge_sources", params={
            "select": "id,status,title,source_key,updated_at",
            "order": "updated_at.desc",
        })
        chunks = client.rows("knowledge_chunks", params={
            "select": "quality_status,classification_confidence,retrieval_scope",
        })
        runs = client.rows("knowledge_ingestion_runs", params={
            "select": "*", "order": "created_at.desc", "limit": 6,
        })
        audit = client.rows("knowledge_audit_log", params={
            "select": "id,actor_email,action,entity_type,reason,created_at",
            "order": "created_at.desc", "limit": 8,
        })
        source_counts = Counter(row["status"] for row in sources)
        chunk_counts = Counter(row["quality_status"] for row in chunks)
        kundlis = client.rows("kundlis", params={"select": "id,user_id,archived_at"})
        readings = client.rows("readings", params={"select": "id,user_rating"})
        profiles = Counter(row["user_id"] for row in kundlis if not row.get("archived_at"))
        confidences = [
            float(row["classification_confidence"])
            for row in chunks if row.get("classification_confidence") is not None
        ]
        return {
            "role": user.role,
            "users": {
                "total": len(auth_users),
                "active_30d": sum(
                    bool(row.get("last_sign_in_at")) for row in auth_users
                ),
                "with_profiles": len(profiles),
            },
            "product": {
                "profiles": sum(profiles.values()),
                "readings": len(readings),
                "rated_readings": sum(row.get("user_rating") is not None for row in readings),
            },
            "sources": {
                "total": len(sources),
                "ready": source_counts["ready"],
                "needs_review": source_counts["needs_review"],
                "failed": source_counts["failed"],
            },
            "chunks": {
                "total": len(chunks),
                "published": chunk_counts["published"],
                "needs_review": chunk_counts["needs_review"],
                "rejected": chunk_counts["rejected"],
                "retrievable": sum(
                    row["quality_status"] == "published"
                    and row["retrieval_scope"] == "core"
                    for row in chunks
                ),
                "excluded": sum(
                    row["retrieval_scope"] != "core"
                    for row in chunks
                ),
                "average_confidence": (
                    round(sum(confidences) / len(confidences), 3) if confidences else None
                ),
            },
            "recent_sources": sources[:6],
            "recent_runs": runs,
            "recent_audit": audit,
        }

    return _safe(load)


@router.get("/users")
def list_users(
    user: AdminUser,
    q: str | None = Query(default=None, max_length=200),
):
    client = _client()

    def load():
        auth_users = client.auth_users()
        kundlis = client.rows("kundlis", params={
            "select": "id,user_id,kind,archived_at",
        })
        threads = client.rows("ask_threads", params={"select": "id,user_id"})
        devices = client.rows("user_devices", params={"select": "id,user_id,last_seen_at"})
        profiles = {
            row["user_id"]: row
            for row in client.rows("user_profiles", params={
                "select": "user_id,display_name,avatar_url,locale,timezone",
            })
        }
        access = {
            row["user_id"]: row
            for row in client.rows("admin_users", params={"select": "user_id,role,active"})
        }
        profile_counts = Counter(
            row["user_id"] for row in kundlis
            if row.get("kind") == "profile" and not row.get("archived_at")
        )
        thread_counts = Counter(row["user_id"] for row in threads)
        device_counts = Counter(row["user_id"] for row in devices)
        needle = (q or "").strip().lower()
        results = []
        for row in auth_users:
            profile = profiles.get(row["id"], {})
            display_name = (
                profile.get("display_name")
                or row.get("user_metadata", {}).get("full_name")
                or row.get("user_metadata", {}).get("name")
            )
            if needle and needle not in " ".join([
                row.get("email") or "", display_name or "", row["id"],
            ]).lower():
                continue
            results.append({
                "id": row["id"],
                "email": row.get("email"),
                "display_name": display_name,
                "avatar_url": profile.get("avatar_url"),
                "locale": profile.get("locale"),
                "timezone": profile.get("timezone"),
                "providers": row.get("app_metadata", {}).get("providers", []),
                "created_at": row.get("created_at"),
                "last_sign_in_at": row.get("last_sign_in_at"),
                "banned_until": row.get("banned_until"),
                "profile_count": profile_counts[row["id"]],
                "thread_count": thread_counts[row["id"]],
                "device_count": device_counts[row["id"]],
                "admin_role": access.get(row["id"], {}).get("role"),
                "admin_active": access.get(row["id"], {}).get("active", False),
            })
        return sorted(
            results,
            key=lambda row: row.get("last_sign_in_at") or row.get("created_at") or "",
            reverse=True,
        )

    return _safe(load)


@router.get("/users/{user_id}")
def user_detail(user_id: str, user: AdminUser):
    client = _client()

    def load():
        auth_user = next(
            (row for row in client.auth_users() if row["id"] == user_id),
            None,
        )
        if not auth_user:
            raise HTTPException(status_code=404, detail="User not found")
        profiles = client.rows("kundlis", params={
            "user_id": f"eq.{user_id}",
            "select": (
                "id,name,relation,kind,birth_city,birth_nation,sun_sign,moon_sign,"
                "ascendant,archived_at,created_at,updated_at"
            ),
            "order": "updated_at.desc",
        })
        profile_ids = [row["id"] for row in profiles]
        readings = []
        if profile_ids:
            readings = client.rows("readings", params={
                "kundli_id": f"in.({','.join(profile_ids)})",
                "select": (
                    "id,kundli_id,reading_type,period_label,version,deviation_score,"
                    "user_rating,reviewed_at,language,generated_at"
                ),
                "order": "generated_at.desc",
                "limit": 50,
            })
        return {
            "auth": {
                "id": auth_user["id"],
                "email": auth_user.get("email"),
                "providers": auth_user.get("app_metadata", {}).get("providers", []),
                "metadata": auth_user.get("user_metadata", {}),
                "created_at": auth_user.get("created_at"),
                "last_sign_in_at": auth_user.get("last_sign_in_at"),
                "banned_until": auth_user.get("banned_until"),
            },
            "profile": client.one("user_profiles", params={
                "user_id": f"eq.{user_id}", "select": "*",
            }),
            "settings": client.one("user_settings", params={
                "user_id": f"eq.{user_id}", "select": "*",
            }),
            "kundlis": profiles,
            "readings": readings,
            "prediction_claims": client.rows("prediction_claims", params={
                "user_id": f"eq.{user_id}",
                "select": (
                    "id,kundli_id,reading_id,category,status,confidence,"
                    "target_start_date,target_end_date,reviewed_at,created_at"
                ),
                "order": "created_at.desc",
                "limit": 50,
            }),
            "ask_threads": client.rows("ask_threads", params={
                "user_id": f"eq.{user_id}",
                "select": "id,kundli_id,title,message_count,last_message_at,archived_at,created_at",
                "order": "created_at.desc",
                "limit": 50,
            }),
            "devices": client.rows("user_devices", params={
                "user_id": f"eq.{user_id}",
                "select": "*",
                "order": "last_seen_at.desc",
            }),
            "remedies": client.rows("user_remedies", params={
                "user_id": f"eq.{user_id}",
                "select": "id,kundli_id,remedy_id,status,started_at,completed_at",
                "order": "created_at.desc",
            }),
            "muhurta_requests": client.rows("muhurta_requests", params={
                "user_id": f"eq.{user_id}",
                "select": "id,kundli_id,goal_slug,date_from,date_to,status,computed_at,created_at",
                "order": "created_at.desc",
                "limit": 50,
            }),
        }

    return _safe(load)


@router.post("/users/{user_id}/status")
def update_user_status(user_id: str, body: UserStatusPayload, user: FullAdminUser):
    if user_id == user.id and body.action == "suspend":
        raise HTTPException(status_code=400, detail="You cannot suspend your own account")
    client = _client()

    def update():
        auth_user = next(
            (row for row in client.auth_users() if row["id"] == user_id),
            None,
        )
        if not auth_user:
            raise HTTPException(status_code=404, detail="User not found")
        after = client.update_auth_user(
            user_id,
            {"ban_duration": "876000h" if body.action == "suspend" else "none"},
        )
        client.audit(
            actor=user, action=f"user.{body.action}", entity_type="user",
            entity_id=user_id, reason=body.reason,
            before={"banned_until": auth_user.get("banned_until")},
            after={"banned_until": after.get("banned_until")},
        )
        return {
            "id": user_id,
            "action": body.action,
            "banned_until": after.get("banned_until"),
        }

    return _safe(update)


@router.get("/activity")
def product_activity(user: AdminUser):
    client = _client()

    def load():
        readings = client.rows("readings", params={
            "select": (
                "id,kundli_id,reading_type,period_label,version,deviation_score,"
                "user_rating,reviewed_at,language,generated_at"
            ),
            "order": "generated_at.desc",
            "limit": 100,
        })
        claims = client.rows("prediction_claims", params={
            "select": "id,user_id,kundli_id,category,status,confidence,reviewed_at,created_at",
            "order": "created_at.desc",
            "limit": 100,
        })
        threads = client.rows("ask_threads", params={
            "select": "id,user_id,kundli_id,title,message_count,last_message_at,created_at",
            "order": "created_at.desc",
            "limit": 100,
        })
        remedies = client.rows("user_remedies", params={
            "select": "id,user_id,status,created_at,completed_at",
            "order": "created_at.desc",
            "limit": 100,
        })
        muhurta = client.rows("muhurta_requests", params={
            "select": "id,user_id,goal_slug,status,computed_at,created_at",
            "order": "created_at.desc",
            "limit": 100,
        })
        return {
            "counts": {
                "readings": len(readings),
                "rated_readings": sum(row.get("user_rating") is not None for row in readings),
                "ask_threads": len(threads),
                "ask_messages": sum(row.get("message_count") or 0 for row in threads),
                "validated_claims": sum(row.get("reviewed_at") is not None for row in claims),
                "active_remedies": sum(row.get("status") == "active" for row in remedies),
                "muhurta_requests": len(muhurta),
            },
            "readings": readings[:30],
            "claims": claims[:30],
            "ask_threads": threads[:30],
            "remedies": remedies[:30],
            "muhurta_requests": muhurta[:30],
        }

    return _safe(load)


@router.get("/system")
def system_health(user: AdminUser):
    client = _client()

    def load():
        table_names = [
            "kundlis", "readings", "prediction_claims", "ask_threads",
            "ask_messages", "user_devices", "user_remedies", "muhurta_requests",
            "knowledge_sources", "knowledge_chunks",
        ]
        counts = {}
        for table in table_names:
            response = client.request(
                "GET", table, params={"select": "id", "limit": 1},
                prefer="count=exact",
            )
            content_range = response.headers.get("content-range", "*/0")
            counts[table] = int(content_range.rsplit("/", 1)[-1] or 0)
        runs = client.rows("knowledge_ingestion_runs", params={
            "select": "*", "order": "created_at.desc", "limit": 30,
        })
        failed = [run for run in runs if run["status"] == "failed"]
        return {
            "status": "healthy" if not failed else "attention",
            "database": "Supabase Postgres",
            "storage_bucket": "astro-knowledge-sources",
            "taxonomy_version": taxonomy_version(),
            "counts": counts,
            "ingestion_runs": runs,
            "failed_runs": len(failed),
        }

    return _safe(load)


@router.get("/sources")
def list_sources(
    user: AdminUser,
    status: str | None = None,
    q: str | None = Query(default=None, max_length=200),
):
    client = _client()

    def load():
        params = {
            "select": "*",
            "order": "updated_at.desc",
        }
        if status:
            params["status"] = f"eq.{status}"
        if q:
            safe_q = q.replace(",", " ").replace("(", " ").replace(")", " ")
            params["or"] = (
                f"(title.ilike.*{safe_q}*,author.ilike.*{safe_q}*,"
                f"source_key.ilike.*{safe_q}*)"
            )
        sources = client.rows("knowledge_sources", params=params)
        chunks = client.rows("knowledge_chunks", params={
            "select": "source_id,quality_status,retrieval_scope",
        })
        counts: dict[str, Counter] = {}
        for row in chunks:
            source_counts = counts.setdefault(row["source_id"], Counter())
            source_counts[row["quality_status"]] += 1
            if (
                row["quality_status"] == "published"
                and row["retrieval_scope"] == "core"
            ):
                source_counts["retrievable"] += 1
            if row["retrieval_scope"] != "core":
                source_counts["excluded"] += 1
        return [{
            **source,
            "chunk_counts": dict(counts.get(source["id"], Counter())),
        } for source in sources]

    return _safe(load)


@router.get("/sources/{source_id}")
def source_detail(source_id: str, user: AdminUser):
    client = _client()

    def load():
        source = client.one("knowledge_sources", params={
            "id": f"eq.{source_id}", "select": "*",
        })
        if not source:
            raise HTTPException(status_code=404, detail="Knowledge source not found")
        sections = client.rows("knowledge_sections", params={
            "source_id": f"eq.{source_id}",
            "select": "id,ordinal,href,title,page_label,text_sha256,extraction_confidence",
            "order": "ordinal",
        })
        chunks = client.rows("knowledge_chunks", params={
            "source_id": f"eq.{source_id}",
            "select": (
                "id,ordinal,title,page_labels,domains,topics,quality_status,"
                "classification_confidence,extraction_confidence,quality_notes,"
                "retrieval_scope,retrieval_exclusion_reason,scope_confidence,"
                "scope_classifier"
            ),
            "order": "ordinal",
        })
        runs = client.rows("knowledge_ingestion_runs", params={
            "source_id": f"eq.{source_id}", "select": "*",
            "order": "created_at.desc", "limit": 10,
        })
        return {"source": source, "sections": sections, "chunks": chunks, "runs": runs}

    return _safe(load)


@router.patch("/sources/{source_id}")
def update_source(source_id: str, body: SourceMetadataPayload, user: FullAdminUser):
    client = _client()

    def update():
        before = client.one("knowledge_sources", params={
            "id": f"eq.{source_id}", "select": "*",
        })
        if not before:
            raise HTTPException(status_code=404, detail="Knowledge source not found")
        payload = body.model_dump(exclude={"reason"}, exclude_none=True)
        if not payload:
            raise HTTPException(status_code=400, detail="No metadata changes supplied")
        after = client.patch(
            "knowledge_sources", params={"id": f"eq.{source_id}"}, payload=payload,
        )[0]
        client.audit(
            actor=user, action="source.metadata_updated", entity_type="source",
            entity_id=source_id, source_id=source_id, reason=body.reason,
            before=before, after=after,
        )
        return after

    return _safe(update)


@router.get("/chunks")
def list_chunks(
    user: AdminUser,
    source_id: str | None = None,
    status: str | None = "needs_review",
    retrieval_scope: str | None = None,
    q: str | None = Query(default=None, max_length=200),
    limit: int = Query(default=100, ge=1, le=250),
):
    client = _client()

    def load():
        params = {
            "select": (
                "id,source_id,ordinal,title,content,page_labels,section_ordinals,"
                "domains,subdomains,source_domains,"
                "topics,content_types,classification_confidence,extraction_confidence,"
                "quality_status,quality_notes,content_sha256,retrieval_scope,"
                "retrieval_exclusion_reason,scope_confidence,scope_classifier"
            ),
            "order": "source_id.asc,ordinal.asc",
            "limit": limit,
        }
        if source_id:
            params["source_id"] = f"eq.{source_id}"
        if status and status != "all":
            params["quality_status"] = f"eq.{status}"
        if retrieval_scope and retrieval_scope != "all":
            params["retrieval_scope"] = f"eq.{retrieval_scope}"
        if q:
            safe_q = q.replace(",", " ").replace("(", " ").replace(")", " ")
            params["or"] = f"(title.ilike.*{safe_q}*,content.ilike.*{safe_q}*)"
        chunks = client.rows("knowledge_chunks", params=params)
        sources = _source_map(client, {row["source_id"] for row in chunks})
        return [{**row, "source": sources.get(row["source_id"])} for row in chunks]

    return _safe(load)


@router.get("/chunks/{chunk_id}")
def chunk_detail(chunk_id: str, user: AdminUser):
    client = _client()

    def load():
        chunk = client.one("knowledge_chunks", params={
            "id": f"eq.{chunk_id}", "select": "*",
        })
        if not chunk:
            raise HTTPException(status_code=404, detail="Knowledge chunk not found")
        source = client.one("knowledge_sources", params={
            "id": f"eq.{chunk['source_id']}", "select": "*",
        })
        audit = client.rows("knowledge_audit_log", params={
            "entity_id": f"eq.{chunk_id}", "select": "*",
            "order": "created_at.desc",
        })
        ordinals = chunk.get("section_ordinals") or []
        sections = []
        if ordinals:
            sections = client.rows("knowledge_sections", params={
                "source_id": f"eq.{chunk['source_id']}",
                "ordinal": f"in.({','.join(str(value) for value in ordinals)})",
                "select": (
                    "id,ordinal,page_label,title,page_image_path,page_image_sha256,"
                    "extraction_method"
                ),
                "order": "ordinal.asc",
            })
        for section in sections:
            path = section.get("page_image_path")
            section["page_image_url"] = (
                client.signed_source_url(source["storage_bucket"], path)
                if path else None
            )
        return {
            "chunk": {**chunk, "page_assets": sections},
            "source": source,
            "audit": audit,
        }

    return _safe(load)


@router.patch("/chunks/{chunk_id}/metadata")
def update_chunk_metadata(chunk_id: str, body: ChunkMetadataPayload, user: AdminUser):
    client = _client()

    def update():
        before = client.one("knowledge_chunks", params={
            "id": f"eq.{chunk_id}", "select": "*",
        })
        if not before:
            raise HTTPException(status_code=404, detail="Knowledge chunk not found")
        payload = body.model_dump(exclude={"reason"}, exclude_none=True)
        if payload.get("retrieval_scope") == "core":
            payload["retrieval_exclusion_reason"] = None
        valid_domains = set(taxonomy())
        if payload.get("domains") and not set(payload["domains"]).issubset(valid_domains):
            raise HTTPException(status_code=400, detail="Unknown CE domain supplied")
        after = client.patch(
            "knowledge_chunks", params={"id": f"eq.{chunk_id}"}, payload=payload,
        )[0]
        client.audit(
            actor=user, action="chunk.metadata_updated", entity_type="chunk",
            entity_id=chunk_id, source_id=before["source_id"], reason=body.reason,
            before=before, after=after,
        )
        return after

    return _safe(update)


def _review_chunk(client, chunk_id: str, body: ReviewPayload, user, request_id=None):
    before = client.one("knowledge_chunks", params={
        "id": f"eq.{chunk_id}", "select": "*",
    })
    if not before:
        raise HTTPException(status_code=404, detail=f"Chunk {chunk_id} not found")
    target = {
        "publish": "published",
        "reject": "rejected",
        "requeue": "needs_review",
    }[body.action]
    after = client.patch(
        "knowledge_chunks",
        params={"id": f"eq.{chunk_id}"},
        payload={"quality_status": target},
    )[0]
    client.audit(
        actor=user, action=f"chunk.{body.action}", entity_type="chunk",
        entity_id=chunk_id, source_id=before["source_id"], reason=body.reason,
        before={"quality_status": before["quality_status"]},
        after={"quality_status": target}, request_id=request_id,
    )
    return after


@router.post("/chunks/{chunk_id}/review")
def review_chunk(chunk_id: str, body: ReviewPayload, user: AdminUser):
    client = _client()

    def review():
        after = _review_chunk(client, chunk_id, body, user)
        _refresh_source_status(client, after["source_id"])
        return after

    return _safe(review)


@router.post("/chunks/bulk-review")
def bulk_review(body: BulkReviewPayload, user: AdminUser):
    client = _client()

    def review():
        request_id = str(uuid4())
        source_ids = set()
        action = ReviewPayload(action=body.action, reason=body.reason)
        for chunk_id in dict.fromkeys(body.chunk_ids):
            after = _review_chunk(client, chunk_id, action, user, request_id)
            source_ids.add(after["source_id"])
        for source_id in source_ids:
            _refresh_source_status(client, source_id)
        return {
            "updated": len(set(body.chunk_ids)),
            "action": body.action,
            "request_id": request_id,
        }

    return _safe(review)


@router.post("/retrieval/test")
def retrieval_test(body: RetrievalTestPayload, user: AdminUser):
    client = _client()

    def retrieve():
        unknown = sorted(set(body.domains) - set(taxonomy()))
        if unknown:
            raise HTTPException(status_code=400, detail=f"Unknown domains: {unknown}")
        rows = SupabaseSourceRetriever(
            client.url, client.secret,
        ).retrieve(body.query, body.domains, body.limit)
        return {"query": body.query, "domains": body.domains, "results": [
            passage.to_dict() for passage in rows
        ]}

    return _safe(retrieve)


@router.get("/taxonomy")
def get_taxonomy(user: AdminUser):
    return {
        "version": taxonomy_version(),
        "domains": [{
            "id": key,
            "name": spec.name,
            "description": spec.description,
            "subdomains": list(spec.subdomains),
            "keywords": list(spec.keywords),
        } for key, spec in taxonomy().items()],
    }


@router.get("/audit")
def audit_log(
    user: AdminUser,
    source_id: str | None = None,
    action: str | None = None,
    actor: str | None = None,
    scope: Literal["all", "admin", "app"] = "all",
    limit: int = Query(default=100, ge=1, le=250),
):
    client = _client()

    def load():
        params = {"select": "*", "order": "created_at.desc", "limit": limit}
        if source_id:
            params["source_id"] = f"eq.{source_id}"
        if action:
            params["action"] = f"eq.{action}"
        if actor:
            params["actor_email"] = f"ilike.*{actor}*"
        rows = []
        if scope in {"all", "admin"}:
            rows.extend(client.rows("knowledge_audit_log", params=params))
        if scope in {"all", "app"} and not source_id:
            app_params = {
                "select": "*", "order": "created_at.desc", "limit": limit,
            }
            if actor:
                app_params["actor_email"] = f"ilike.*{actor}*"
            app_rows = client.rows("app_request_audit_log", params=app_params)
            rows.extend({
                "id": row["id"],
                "actor_id": row.get("actor_id"),
                "actor_email": row.get("actor_email"),
                "actor_role": "user",
                "action": f"{row['method']} {row['route']}",
                "entity_type": row.get("resource_type") or "request",
                "entity_id": row.get("resource_id"),
                "source_id": None,
                "reason": f"HTTP {row['status_code']} · {row.get('duration_ms') or 0} ms",
                "before_state": None,
                "after_state": row.get("metadata"),
                "request_id": row["request_id"],
                "created_at": row["created_at"],
            } for row in app_rows)
        if action:
            rows = [row for row in rows if row["action"] == action]
        rows.sort(key=lambda row: row["created_at"], reverse=True)
        return rows[:limit]

    return _safe(load)


@router.post("/sources/upload")
async def upload_source(
    background: BackgroundTasks,
    user: FullAdminUser,
    file: UploadFile = File(...),
    source_key: str = Form(..., min_length=2, max_length=96),
    start_section: int = Form(0, ge=0),
    max_sections: int | None = Form(None, ge=1),
):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".epub", ".pdf"}:
        raise HTTPException(status_code=400, detail="Only PDF and EPUB uploads are supported")
    normalized = re.sub(r"[^a-z0-9]+", "-", source_key.lower()).strip("-")
    if normalized != source_key:
        raise HTTPException(
            status_code=400,
            detail="Source key must use lowercase letters, numbers, and hyphens",
        )
    payload = await file.read(100 * 1024 * 1024 + 1)
    if len(payload) > 100 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Source exceeds the 100 MB limit")
    client = _client()

    def queue():
        folder = "pdfs" if suffix == ".pdf" else "epubs"
        storage_path = f"{folder}/{source_key}{suffix}"
        client.upload_source(
            "astro-knowledge-sources",
            storage_path,
            payload,
            "application/pdf" if suffix == ".pdf" else "application/epub+zip",
        )
        handle = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
        try:
            handle.write(payload)
            handle.close()
        except Exception:
            Path(handle.name).unlink(missing_ok=True)
            raise
        run = client.insert("knowledge_ingestion_runs", {
            "source_key": source_key,
            "status": "queued",
            "requested_by": user.id if user.auth_enabled else None,
            "analyzer_model": "claude-opus-5",
            "start_section": start_section,
            "max_sections": max_sections,
        })[0]
        client.audit(
            actor=user, action="source.ingestion_queued", entity_type="ingestion_run",
            entity_id=run["id"], reason=f"Uploaded {file.filename}",
            after={
                "source_key": source_key,
                "storage_path": storage_path,
                "start_section": start_section,
                "max_sections": max_sections,
            },
        )
        background.add_task(
            run_ingestion_job,
            client=client,
            run_id=run["id"],
            local_path=handle.name,
            storage_path=storage_path,
            source_key=source_key,
            start_section=start_section,
            max_sections=max_sections,
        )
        return {"run_id": run["id"], "status": "queued", "source_key": source_key}

    return _safe(queue)


@router.post("/sources/{source_id}/reprocess")
def reprocess_source(
    source_id: str,
    background: BackgroundTasks,
    user: FullAdminUser,
    start_section: int = Query(default=0, ge=0),
    max_sections: int | None = Query(default=None, ge=1),
):
    client = _client()

    def queue():
        source = client.one("knowledge_sources", params={
            "id": f"eq.{source_id}", "select": "*",
        })
        if not source:
            raise HTTPException(status_code=404, detail="Knowledge source not found")
        payload = client.download_source(source["storage_bucket"], source["storage_path"])
        suffix = ".pdf" if source.get("file_type") == "pdf" else ".epub"
        handle = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
        handle.write(payload)
        handle.close()
        run = client.insert("knowledge_ingestion_runs", {
            "source_id": source_id,
            "source_key": source["source_key"],
            "status": "queued",
            "requested_by": user.id if user.auth_enabled else None,
            "analyzer_model": "claude-opus-5",
            "start_section": start_section,
            "max_sections": max_sections,
        })[0]
        client.audit(
            actor=user, action="source.reprocess_queued", entity_type="ingestion_run",
            entity_id=run["id"], source_id=source_id,
            reason="Administrator requested source reprocessing",
            after={"start_section": start_section, "max_sections": max_sections},
        )
        background.add_task(
            run_ingestion_job,
            client=client,
            run_id=run["id"],
            local_path=handle.name,
            storage_path=source["storage_path"],
            source_key=source["source_key"],
            start_section=start_section,
            max_sections=max_sections,
        )
        return {"run_id": run["id"], "status": "queued"}

    return _safe(queue)


@router.get("/access")
def list_access(user: FullAdminUser):
    client = _client()

    def load():
        assignments = {
            row["user_id"]: row
            for row in client.rows("admin_users", params={"select": "*"})
        }
        return [{
            "user_id": auth_user["id"],
            "email": auth_user.get("email"),
            "name": (
                auth_user.get("user_metadata", {}).get("full_name")
                or auth_user.get("user_metadata", {}).get("name")
            ),
            "last_sign_in_at": auth_user.get("last_sign_in_at"),
            "role": assignments.get(auth_user["id"], {}).get("role"),
            "active": assignments.get(auth_user["id"], {}).get("active", False),
        } for auth_user in client.auth_users()]

    return _safe(load)


@router.put("/access/{user_id}")
def update_access(user_id: str, body: AccessPayload, user: FullAdminUser):
    if user_id == user.id and not body.active:
        raise HTTPException(status_code=400, detail="You cannot deactivate your own access")
    client = _client()

    def update():
        before = client.one("admin_users", params={
            "user_id": f"eq.{user_id}", "select": "*",
        })
        rows = client.request(
            "POST", "admin_users",
            params={"on_conflict": "user_id"},
            json={"user_id": user_id, "role": body.role, "active": body.active},
            prefer="resolution=merge-duplicates,return=representation",
        ).json()
        after = rows[0]
        client.audit(
            actor=user, action="access.updated", entity_type="admin_user",
            entity_id=user_id, reason=body.reason, before=before, after=after,
        )
        return after

    return _safe(update)
