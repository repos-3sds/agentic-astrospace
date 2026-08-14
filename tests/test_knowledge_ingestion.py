import json
from pathlib import Path

import pytest

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

# These fixture files are the real ~318MB corpus (.gitignore'd: "ingestion
# inputs, not code — they live in Supabase storage"), not something CI
# checks out. Skip rather than fail red where they're absent; every test
# below still runs locally against the real corpus, which is the only place
# they can meaningfully exercise real EPUB/PDF/OCR extraction anyway — a
# synthetic fixture would just be testing the parser against itself.
_requires_epub = pytest.mark.skipif(
    not EPUB.exists(), reason="requires the local knowledge-base corpus (not present in CI)"
)
_requires_pdf = pytest.mark.skipif(
    not PDF.exists(), reason="requires the local knowledge-base corpus (not present in CI)"
)
_requires_mistral_export = pytest.mark.skipif(
    not MISTRAL_EXPORT.exists(),
    reason="requires the local knowledge-base corpus (not present in CI)",
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


class _CleanAnalyzer:
    """One high-confidence chunk with no notes, so the quality gate is the only
    thing that can hold a passage back."""

    def analyze(self, blocks):
        return [ChunkPlan(
            start_block_id=blocks[0].id,
            end_block_id=blocks[-1].id,
            title="Source passage",
            confidence=0.95,
        )]


def _build_chunks(text: str, source_key: str = "synthetic"):
    """Run build_chunks over a synthetic one-block book."""
    import hashlib

    from astrospace.knowledge.ingestion.models import (
        EpubBook, EpubSection, TextBlock,
    )

    block = TextBlock(id="b0", section_ordinal=0, block_ordinal=0,
                      href="s0.xhtml", tag="p", text=text, page_label="1")
    digest = hashlib.sha256(text.encode()).hexdigest()
    section = EpubSection(ordinal=0, href="s0.xhtml", title="S", page_label="1",
                          blocks=(block,), exact_text=text,
                          text_sha256=digest, raw_xhtml_sha256=digest,
                          extraction_method="epub_xhtml")
    book = EpubBook(source_key=source_key, title="Synthetic", author=None,
                    language="sa", identifier=None, sha256=digest,
                    sections=(section,))
    return IngestionPipeline(
        MemoryRepository(), analyzer=_CleanAnalyzer()
    ).build_chunks(book)


class TestLalKitabSourcePolicy:
    def test_catalog_names_the_edition_and_distinct_tradition(self):
        catalog = json.loads(Path("astrospace/context/sources.json").read_text())
        source = catalog["sources"]["lal_kitab_1952"]

        assert source["ingestion_source_key"] == "lal-kitab-1952-roop-chand-joshi"
        assert source["tradition"] == "Lal Kitab"
        assert "not a Parashari authority" in source["caveat"]
        assert "human review" in source["caveat"]

    def test_lal_kitab_passages_are_tagged_and_held_for_review(self):
        chunks = _build_chunks(
            "A house-specific traditional remedy is described in this passage.",
            source_key="lal-kitab-1952-roop-chand-joshi",
        )

        assert chunks
        for chunk in chunks:
            assert chunk.quality_status == "needs_review"
            assert "lal_kitab_tradition" in chunk.source_domains
            assert "traditional_remedies" in chunk.source_domains
            assert "lal_kitab_remedies" in chunk.topics
            assert any(
                "edition-aware human review" in note
                for note in chunk.quality_notes
            )

    def test_lal_kitab_policy_does_not_change_other_sources(self):
        chunks = _build_chunks(
            "The lord of the tenth house supports professional responsibility.",
            source_key="brihat-parasara-hora-sastra-volume-1",
        )

        assert chunks
        assert all("lal_kitab_tradition" not in chunk.source_domains for chunk in chunks)
        assert all("lal_kitab_remedies" not in chunk.topics for chunk in chunks)
        assert all(
            not any("edition-aware human review" in note for note in chunk.quality_notes)
            for chunk in chunks
        )



@_requires_epub
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


@_requires_epub
def test_epub_extractor_can_skip_front_matter_without_changing_ordinals():
    book = EpubExtractor().extract(EPUB, start_section=15, max_sections=2)
    assert [section.ordinal for section in book.sections] == [15, 16]
    assert [section.page_label for section in book.sections] == ["14", "15"]


@_requires_epub
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


@_requires_epub
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


@_requires_pdf
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


@_requires_pdf
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


@_requires_mistral_export
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


@_requires_mistral_export
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


class TestDegenerateEmbeddings:
    """A chunk the embedder cannot represent must not reach retrieval unseen.

    FeatureHashEmbedder tokenises on a Latin-initial pattern, so Devanagari-only
    passages produce an all-zero vector. pgvector then reports NaN for cosine
    distance and Postgres orders NaN above every real value, which put twelve
    such chunks at the top of every search in the live corpus.
    """

    def test_devanagari_only_text_is_degenerate(self):
        from astrospace.knowledge.ingestion.embeddings import (
            FeatureHashEmbedder, is_degenerate,
        )
        embedder = FeatureHashEmbedder()
        assert is_degenerate(embedder.embed("अथ राजयोगाध्यायः ॥४१॥"))
        assert is_degenerate(embedder.embed("|  0, |  | 0, | 0, |  |"))
        assert is_degenerate(embedder.embed(""))

    def test_ordinary_english_is_not_degenerate(self):
        from astrospace.knowledge.ingestion.embeddings import (
            FeatureHashEmbedder, is_degenerate,
        )
        vector = FeatureHashEmbedder().embed(
            "The lord of the ascendant in the tenth house gives high office."
        )
        assert not is_degenerate(vector)
        assert abs(sum(v * v for v in vector) - 1.0) < 1e-9, "must stay normalised"

    def test_degenerate_chunk_is_held_for_review(self):
        """The gate that already exists does the work — no new mechanism."""
        from astrospace.knowledge.ingestion.embeddings import is_degenerate

        chunks = _build_chunks("॥ श्रीः ॥\n\nअथ राजयोगाध्यायः ॥४१॥")
        degenerate = [c for c in chunks if is_degenerate(c.embedding)]
        assert degenerate, "expected the Devanagari passage to be degenerate"
        for chunk in degenerate:
            assert chunk.quality_status == "needs_review"
            assert any("no embedding signal" in n for n in chunk.quality_notes)

    def test_normal_chunk_still_auto_publishes(self):
        """The new note must not sweep up healthy passages."""
        chunks = _build_chunks(
            "Sloka 50. The person born with Jupiter in the ninth house "
            "acquires learning, wealth and a reputation for fairness."
        )
        assert chunks
        assert all(c.quality_status == "published" for c in chunks)
        assert all(
            not any("no embedding signal" in n for n in c.quality_notes)
            for c in chunks
        )
