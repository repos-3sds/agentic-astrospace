from __future__ import annotations

from collections import Counter, defaultdict
import json
from pathlib import Path
import sys

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from astrospace.admin.client import SupabaseAdminClient
from astrospace.knowledge.ingestion.scope import classify_retrieval_scope


def _batches(values: list[str], size: int = 50):
    for offset in range(0, len(values), size):
        yield values[offset:offset + size]


def main() -> None:
    load_dotenv()
    client = SupabaseAdminClient()
    sources = client.rows("knowledge_sources", params={
        "parser_version": "eq.mistral-ocr-playground-v1",
        "select": "id,source_key,title",
        "order": "source_key",
    })
    summary = {}
    for source in sources:
        chunks = client.rows("knowledge_chunks", params={
            "source_id": f"eq.{source['id']}",
            "select": (
                "id,ordinal,title,content,retrieval_scope,"
                "retrieval_exclusion_reason,scope_confidence,scope_classifier"
            ),
            "order": "ordinal",
        })
        groups: dict[tuple, list[str]] = defaultdict(list)
        counts = Counter()
        changed = 0
        for chunk in chunks:
            decision = classify_retrieval_scope(
                source["source_key"],
                int(chunk["ordinal"]),
                chunk.get("title") or "",
                chunk.get("content") or "",
            )
            counts[decision.scope] += 1
            current = (
                chunk.get("retrieval_scope"),
                chunk.get("retrieval_exclusion_reason"),
                chunk.get("scope_confidence"),
                chunk.get("scope_classifier"),
            )
            target = (
                decision.scope,
                decision.reason,
                decision.confidence,
                decision.classifier,
            )
            if current != target:
                groups[target].append(chunk["id"])
                changed += 1
        for target, ids in groups.items():
            scope, reason, confidence, classifier = target
            for batch in _batches(ids):
                client.patch(
                    "knowledge_chunks",
                    params={"id": f"in.({','.join(batch)})"},
                    payload={
                        "retrieval_scope": scope,
                        "retrieval_exclusion_reason": reason,
                        "scope_confidence": confidence,
                        "scope_classifier": classifier,
                    },
                )
        if changed:
            client.insert("knowledge_audit_log", {
                "action": "source.retrieval_scope_classified",
                "entity_type": "source",
                "entity_id": source["id"],
                "source_id": source["id"],
                "reason": (
                    "Separated core astrology from editorial, navigation, "
                    "publishing and out-of-domain material"
                ),
                "after_state": {
                    "classifier": "curated-edition-boundaries-v1",
                    "counts": dict(counts),
                    "updated_chunks": changed,
                },
            })
        summary[source["source_key"]] = {
            "total": len(chunks),
            "updated": changed,
            "scopes": dict(counts),
        }
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
