from pathlib import Path

from astrospace.knowledge.ingestion.analyzer import HeuristicChunkAnalyzer
from astrospace.knowledge.ingestion.epub import EpubExtractor
from astrospace.knowledge.ingestion.models import ChunkPlan
from astrospace.knowledge.ingestion.pipeline import IngestionPipeline


EPUB = Path(
    "Astro Space Knowledge Base/EPUBS/"
    "Uttara kalamritam..epub"
)


class MemoryRepository:
    def __init__(self):
        self.book = None
        self.chunks = None

    def replace(self, book, chunks, **kwargs):
        self.book = book
        self.chunks = chunks
        return "source-test"


class WarningAnalyzer:
    def analyze(self, blocks):
        return [ChunkPlan(
            start_block_id=blocks[0].id,
            end_block_id=blocks[-1].id,
            title="Warned source passage",
            confidence=0.95,
            quality_notes=("OCR corruption detected",),
        )]


def test_epub_extractor_preserves_spine_and_hashes():
    book = EpubExtractor().extract(EPUB, max_sections=6)
    assert book.title
    assert book.sections
    assert [section.ordinal for section in book.sections] == sorted(
        section.ordinal for section in book.sections
    )
    assert all(section.exact_text for section in book.sections)
    assert all(len(section.text_sha256) == 64 for section in book.sections)
    assert all(len(section.raw_xhtml_sha256) == 64 for section in book.sections)


def test_epub_extractor_can_skip_front_matter_without_changing_ordinals():
    book = EpubExtractor().extract(EPUB, start_section=15, max_sections=2)
    assert [section.ordinal for section in book.sections] == [15, 16]
    assert [section.page_label for section in book.sections] == ["14", "15"]


def test_pipeline_content_is_assembled_only_from_source_blocks():
    repository = MemoryRepository()
    pipeline = IngestionPipeline(
        repository,
        analyzer=HeuristicChunkAnalyzer(),
        max_window_chars=5000,
        max_window_blocks=4,
    )
    result = pipeline.ingest(
        EPUB,
        storage_path="epubs/uttara-kalamritam.epub",
        max_sections=8,
    )
    source_texts = {block.text for block in repository.book.blocks}
    assert result["chunks"] == len(repository.chunks)
    assert repository.chunks
    for chunk in repository.chunks:
        assert chunk.content
        assert all(part in source_texts for part in chunk.content.split("\n\n"))
        assert chunk.quality_status == "needs_review"


def test_analyzer_quality_warning_blocks_publication():
    repository = MemoryRepository()
    result = IngestionPipeline(repository, analyzer=WarningAnalyzer()).ingest(
        EPUB,
        storage_path="epubs/uttara-kalamritam.epub",
        start_section=15,
        max_sections=1,
    )
    assert result["published"] == 0
    assert result["needs_review"] == 1
