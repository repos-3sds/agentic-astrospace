from pathlib import Path

from astrospace.knowledge.ingestion.analyzer import (
    AutomatedChunkAnalyzer,
    HeuristicChunkAnalyzer,
)
from astrospace.knowledge.ingestion.epub import EpubExtractor
from astrospace.knowledge.ingestion.mistral import MistralOcrExtractor
from astrospace.knowledge.ingestion.models import ChunkPlan
from astrospace.knowledge.ingestion.pdf import PdfExtractor
from astrospace.knowledge.ingestion.pipeline import IngestionPipeline


EPUB = Path(
    "Astro Space Knowledge Base/EPUBS/"
    "Uttara kalamritam..epub"
)
PDF = Path(
    "Astro Space Knowledge Base/PDFs/"
    "Uttara kalamritam..pdf"
)
MISTRAL_EXPORT = Path(
    "Astro Space Knowledge Base/ocr-playground-download-20260726T003631Z/"
    "Uttara kalamritam..pdf"
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


class DynamicDomainAnalyzer:
    def analyze(self, blocks):
        return [ChunkPlan(
            start_block_id=blocks[0].id,
            end_block_id=blocks[-1].id,
            title="Invocation and source introduction",
            source_domains=("classical_invocation", "horoscopy_method"),
            domains=(),
            confidence=0.92,
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


def test_pdf_extractor_keeps_page_image_text_and_number_together():
    book = PdfExtractor().extract(
        PDF,
        source_key="uttara-kalamritam-pdf",
        start_section=15,
        max_sections=1,
    )
    section = book.sections[0]
    assert book.file_type == "pdf"
    assert section.page_label == "16"
    assert section.page_image
    assert section.page_image_path == "pages/uttara-kalamritam-pdf/page-0016.jpg"
    assert len(section.page_image_sha256) == 64
    assert section.exact_text
    assert section.extraction_method == "pdf_text_layer"


def test_pdf_pipeline_discovers_domains_without_forcing_ce_mapping():
    repository = MemoryRepository()
    result = IngestionPipeline(
        repository,
        analyzer=DynamicDomainAnalyzer(),
    ).ingest(
        PDF,
        storage_path="pdfs/uttara-kalamritam.pdf",
        source_key="uttara-kalamritam-pdf",
        start_section=15,
        max_sections=1,
    )
    assert result["needs_review"] == len(repository.chunks)
    assert repository.chunks
    assert all(chunk.domains == () for chunk in repository.chunks)
    assert all(
        chunk.source_domains == ("classical_invocation", "horoscopy_method")
        for chunk in repository.chunks
    )
    assert all(
        "PDF page evidence requires human verification" in chunk.quality_notes
        for chunk in repository.chunks
    )


def test_mistral_export_preserves_sanskrit_blocks_and_provenance():
    book = MistralOcrExtractor(
        source_path=PDF,
        title="Uttara Kalamritam",
        export_storage_path="ocr/mistral/uttara-kalamritam/ocr-export.zip",
    ).extract(
        MISTRAL_EXPORT,
        source_key="uttara-kalamritam",
        start_section=49,
        max_sections=1,
    )
    section = book.sections[0]
    assert book.metadata["ocr_provider"] == "mistral"
    assert book.metadata["ocr_export_sha256"]
    assert section.ordinal == 49
    assert section.page_label == "52"
    assert section.extraction_method == "mistral_ocr"
    assert section.extraction_confidence > 0.98
    assert "प्राक्तव्यक्त" in section.exact_text
    assert any("प्राक्तव्यक्त" in block.text for block in section.blocks)
    assert section.metadata["dimensions"]["dpi"] == 130
    assert section.metadata["blocks"]


def test_mistral_high_confidence_chunks_are_auto_published():
    repository = MemoryRepository()
    extractor = MistralOcrExtractor(
        source_path=PDF,
        title="Uttara Kalamritam",
    )
    result = IngestionPipeline(
        repository,
        analyzer=AutomatedChunkAnalyzer(),
        extractor=extractor,
        audit_sample_rate=0,
    ).ingest(
        MISTRAL_EXPORT,
        storage_path="pdfs/uttara-kalamritam.pdf",
        source_key="uttara-kalamritam",
        start_section=49,
        max_sections=1,
    )
    assert result["published"] == result["chunks"]
    assert result["needs_review"] == 0
    assert all(chunk.source_domains for chunk in repository.chunks)
    assert all(
        "PDF page evidence requires human verification" not in chunk.quality_notes
        for chunk in repository.chunks
    )
