from __future__ import annotations

import hashlib
from pathlib import Path

from .analyzer import AnthropicChunkAnalyzer, ChunkAnalyzer
from .embeddings import FeatureHashEmbedder
from .epub import EpubExtractor
from .models import EpubBook, KnowledgeChunk, TextBlock
from .repository import KnowledgeRepository


class IngestionPipeline:
    def __init__(self, repository: KnowledgeRepository, *,
                 analyzer: ChunkAnalyzer | None = None,
                 extractor: EpubExtractor | None = None,
                 embedder: FeatureHashEmbedder | None = None,
                 max_window_chars: int = 16000,
                 max_window_blocks: int = 12):
        self.repository = repository
        self.analyzer = analyzer or AnthropicChunkAnalyzer()
        self.extractor = extractor or EpubExtractor()
        self.embedder = embedder or FeatureHashEmbedder()
        self.max_window_chars = max_window_chars
        self.max_window_blocks = max_window_blocks

    def ingest(self, epub_path: str | Path, *, storage_path: str,
               storage_bucket: str = "astro-knowledge-sources",
               source_key: str | None = None,
               start_section: int = 0,
               max_sections: int | None = None) -> dict:
        book = self.extractor.extract(
            epub_path, source_key=source_key, start_section=start_section,
            max_sections=max_sections,
        )
        chunks = self.build_chunks(book)
        source_id = self.repository.replace(
            book, chunks, storage_bucket=storage_bucket,
            storage_path=storage_path, parser_version=self.extractor.parser_version,
        )
        return {
            "source_id": source_id,
            "source_key": book.source_key,
            "sections": len(book.sections),
            "chunks": len(chunks),
            "published": sum(c.quality_status == "published" for c in chunks),
            "needs_review": sum(c.quality_status == "needs_review" for c in chunks),
        }

    def build_chunks(self, book: EpubBook) -> list[KnowledgeChunk]:
        chunks = []
        ordinal = 0
        for window in self._windows(list(book.blocks)):
            plans = self._validated_plans(window)
            positions = {block.id: index for index, block in enumerate(window)}
            for plan in plans:
                selected = window[
                    positions[plan.start_block_id]:positions[plan.end_block_id] + 1
                ]
                content = "\n\n".join(block.text for block in selected)
                extraction = [
                    block.extraction_confidence
                    for block in selected
                    if block.extraction_confidence is not None
                ]
                extraction_confidence = min(extraction) if extraction else None
                notes = list(plan.quality_notes)
                if extraction_confidence is not None and extraction_confidence < 0.75:
                    notes.append(f"source OCR confidence {extraction_confidence:.2f}")
                fidelity_ok = all(block.text in content for block in selected)
                quality_status = (
                    "published"
                    if fidelity_ok
                    and plan.confidence >= 0.70
                    and not notes
                    and (extraction_confidence is None or extraction_confidence >= 0.75)
                    else "needs_review"
                )
                chunks.append(KnowledgeChunk(
                    ordinal=ordinal,
                    title=plan.title,
                    content=content,
                    content_sha256=hashlib.sha256(content.encode()).hexdigest(),
                    start_block_id=plan.start_block_id,
                    end_block_id=plan.end_block_id,
                    section_ordinals=tuple(dict.fromkeys(
                        block.section_ordinal for block in selected
                    )),
                    page_labels=tuple(dict.fromkeys(
                        block.page_label for block in selected if block.page_label
                    )),
                    domains=plan.domains,
                    subdomains=plan.subdomains,
                    topics=plan.topics,
                    content_types=plan.content_types,
                    classification_confidence=plan.confidence,
                    extraction_confidence=extraction_confidence,
                    quality_status=quality_status,
                    quality_notes=tuple(dict.fromkeys(notes)),
                    embedding=self.embedder.embed(content),
                    embedding_provider=self.embedder.provider,
                ))
                ordinal += 1
        return chunks

    def _validated_plans(self, blocks: list[TextBlock]):
        plans = self.analyzer.analyze(blocks)
        positions = {block.id: index for index, block in enumerate(blocks)}
        cursor = 0
        valid = []
        for plan in plans:
            start = positions.get(plan.start_block_id)
            end = positions.get(plan.end_block_id)
            if start is None or end is None or start != cursor or end < start:
                return self._fallback_plan(blocks)
            valid.append(plan)
            cursor = end + 1
        if cursor != len(blocks):
            return self._fallback_plan(blocks)
        return valid

    def _fallback_plan(self, blocks: list[TextBlock]):
        from .analyzer import HeuristicChunkAnalyzer
        return HeuristicChunkAnalyzer().analyze(blocks)

    def _windows(self, blocks: list[TextBlock]):
        window = []
        chars = 0
        for block in blocks:
            if window and (
                len(window) >= self.max_window_blocks
                or chars + len(block.text) > self.max_window_chars
            ):
                yield window
                window, chars = [], 0
            window.append(block)
            chars += len(block.text)
        if window:
            yield window
