from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class TextBlock:
    id: str
    section_ordinal: int
    block_ordinal: int
    href: str
    tag: str
    text: str
    page_label: str | None = None
    extraction_confidence: float | None = None
    quality_notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class EpubSection:
    ordinal: int
    href: str
    title: str | None
    page_label: str | None
    blocks: tuple[TextBlock, ...]
    exact_text: str
    text_sha256: str
    raw_xhtml_sha256: str
    extraction_confidence: float | None = None
    page_image: bytes | None = None
    page_image_path: str | None = None
    page_image_sha256: str | None = None
    extraction_method: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EpubBook:
    source_key: str
    title: str
    author: str | None
    language: str | None
    identifier: str | None
    sha256: str
    sections: tuple[EpubSection, ...]
    file_type: str = "epub"
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def blocks(self) -> tuple[TextBlock, ...]:
        return tuple(block for section in self.sections for block in section.blocks)


@dataclass(frozen=True)
class ChunkPlan:
    start_block_id: str
    end_block_id: str
    title: str
    domains: tuple[str, ...] = ()
    subdomains: tuple[str, ...] = ()
    topics: tuple[str, ...] = ()
    content_types: tuple[str, ...] = ()
    source_domains: tuple[str, ...] = ()
    confidence: float = 0.0
    quality_notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class KnowledgeChunk:
    ordinal: int
    title: str
    content: str
    content_sha256: str
    start_block_id: str
    end_block_id: str
    section_ordinals: tuple[int, ...]
    page_labels: tuple[str, ...]
    domains: tuple[str, ...]
    subdomains: tuple[str, ...]
    topics: tuple[str, ...]
    content_types: tuple[str, ...]
    classification_confidence: float
    extraction_confidence: float | None
    quality_status: str
    quality_notes: tuple[str, ...] = field(default_factory=tuple)
    embedding: tuple[float, ...] | None = None
    embedding_provider: str | None = None
    source_domains: tuple[str, ...] = field(default_factory=tuple)
    retrieval_scope: str = "core"
    retrieval_exclusion_reason: str | None = None
    scope_confidence: float = 1.0
    scope_classifier: str = "default-core-v1"
