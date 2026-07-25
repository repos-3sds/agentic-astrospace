from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

from .models import EpubBook, EpubSection, TextBlock


_DEVANAGARI_RE = re.compile(r"[\u0900-\u097f]")
_CORRUPTION_RE = re.compile(
    r"(?:lfi,q|lfCl|Q6ICfj|O1~|\\:lCR|[~]{3,}|\ufffd)",
    re.IGNORECASE,
)


def _sha256(value: bytes | str) -> str:
    if isinstance(value, str):
        value = value.encode("utf-8")
    return hashlib.sha256(value).hexdigest()


def _page_number(path: Path) -> int:
    return int(path.name.rsplit("-", 1)[-1])


class MistralOcrExtractor:
    """Read a page-scoped export downloaded from the Mistral OCR playground."""

    parser_version = "mistral-ocr-playground-v1"

    def __init__(
        self,
        *,
        source_path: str | Path,
        title: str | None = None,
        author: str | None = None,
        language: str | None = "sa,en",
        export_storage_path: str | None = None,
        ocr_model: str = "mistral-ocr-latest",
        exported_at: str | None = None,
    ):
        self.source_path = Path(source_path)
        self.title = title
        self.author = author
        self.language = language
        self.export_storage_path = export_storage_path
        self.ocr_model = ocr_model
        self.exported_at = exported_at

    def extract(
        self,
        path: str | Path,
        *,
        source_key: str | None = None,
        start_section: int = 0,
        max_sections: int | None = None,
    ) -> EpubBook:
        export_path = Path(path)
        pages_path = export_path / "pages"
        if not pages_path.is_dir():
            raise ValueError(f"Mistral export has no pages directory: {export_path}")
        if not self.source_path.is_file():
            raise ValueError(f"Original source PDF is missing: {self.source_path}")

        all_pages = sorted(
            (item for item in pages_path.iterdir() if item.is_dir()),
            key=_page_number,
        )
        selected = all_pages[start_section:]
        if max_sections is not None:
            selected = selected[:max_sections]
        key = source_key or self._slug(self.source_path.stem)
        source_payload = self.source_path.read_bytes()
        export_hash = self._export_hash(export_path)
        sections = tuple(self._page(item, key) for item in selected)
        return EpubBook(
            source_key=key,
            title=self.title or self.source_path.stem,
            author=self.author,
            language=self.language,
            identifier=None,
            sha256=_sha256(source_payload),
            sections=sections,
            file_type="pdf",
            metadata={
                "ocr_provider": "mistral",
                "ocr_model": self.ocr_model,
                "ocr_export_sha256": export_hash,
                "ocr_export_storage_path": self.export_storage_path,
                "ocr_exported_at": self.exported_at,
                "source_filename": self.source_path.name,
                "ingested_at": datetime.now(timezone.utc).isoformat(),
            },
        )

    def _page(self, page_path: Path, source_key: str) -> EpubSection:
        page_number = _page_number(page_path)
        markdown = self._read(page_path / "markdown.md")
        header = self._read(page_path / "header.md")
        footer = self._read(page_path / "footer.md")
        metadata_payload = (page_path / "page-metadata.json").read_bytes()
        metadata = json.loads(metadata_payload)
        confidence = metadata.get("confidenceScores") or {}
        average_confidence = confidence.get("averagePageConfidenceScore")
        minimum_confidence = confidence.get("minimumPageConfidenceScore")
        printed_label = self._printed_page_label(header)
        page_label = printed_label or str(page_number)
        page_notes, low_confidence_words = self._quality_notes(
            markdown,
            confidence.get("wordConfidenceScores") or [],
            average_confidence,
        )
        body_blocks = [
            block
            for block in metadata.get("blocks") or []
            if block.get("type") not in {"header", "footer"}
            and str(block.get("content") or "").strip()
        ]
        if not body_blocks and markdown.strip():
            body_blocks = [
                {"type": "text", "content": value}
                for value in re.split(r"\n\s*\n", markdown)
                if value.strip()
            ]
        blocks = tuple(
            TextBlock(
                id=f"p{page_number:04d}-b{ordinal:04d}",
                section_ordinal=page_number - 1,
                block_ordinal=ordinal,
                href=f"page:{page_number}",
                tag=str(block.get("type") or "text"),
                text=str(block.get("content") or "").strip(),
                page_label=page_label,
                extraction_confidence=average_confidence,
                quality_notes=page_notes,
            )
            for ordinal, block in enumerate(body_blocks)
        )
        compact_blocks = [{
            "type": block.get("type"),
            "top_left_x": block.get("topLeftX"),
            "top_left_y": block.get("topLeftY"),
            "bottom_right_x": block.get("bottomRightX"),
            "bottom_right_y": block.get("bottomRightY"),
        } for block in body_blocks]
        return EpubSection(
            ordinal=page_number - 1,
            href=f"page:{page_number}",
            title=f"Page {page_label}",
            page_label=page_label,
            blocks=blocks,
            exact_text=markdown,
            text_sha256=_sha256(markdown),
            raw_xhtml_sha256=_sha256(metadata_payload),
            extraction_confidence=average_confidence,
            extraction_method="mistral_ocr",
            metadata={
                "pdf_page_number": page_number,
                "printed_page_label": printed_label,
                "header": header or None,
                "footer": footer or None,
                "dimensions": metadata.get("dimensions"),
                "minimum_word_confidence": minimum_confidence,
                "low_confidence_words": low_confidence_words,
                "quality_notes": list(page_notes),
                "blocks": compact_blocks,
            },
        )

    @staticmethod
    def _quality_notes(
        markdown: str,
        word_scores: list[dict],
        average_confidence: float | None,
    ) -> tuple[tuple[str, ...], list[dict]]:
        notes = []
        if _CORRUPTION_RE.search(markdown):
            notes.append("possible OCR corruption signature")
        if average_confidence is not None and average_confidence < 0.90:
            notes.append(f"page OCR confidence {average_confidence:.2f}")
        sanskrit_scores = [
            row for row in word_scores
            if _DEVANAGARI_RE.search(str(row.get("text") or ""))
            and isinstance(row.get("confidence"), (int, float))
        ]
        low_confidence_sanskrit = [
            {
                "text": str(row.get("text") or "").strip(),
                "confidence": round(float(row["confidence"]), 4),
            }
            for row in sanskrit_scores
            if float(row["confidence"]) < 0.70
        ]
        severe_sanskrit = [
            row for row in sanskrit_scores
            if float(row["confidence"]) < 0.50
        ]
        if (
            sanskrit_scores
            and len(severe_sanskrit) / len(sanskrit_scores) > 0.10
        ):
            notes.append("low-confidence Sanskrit OCR")
        return tuple(notes), low_confidence_sanskrit[:50]

    @staticmethod
    def _printed_page_label(header: str) -> str | None:
        for line in header.splitlines():
            value = line.strip()
            if re.fullmatch(r"(?:\d{1,4}|[ivxlcdm]{1,10})", value, re.IGNORECASE):
                return value
        return None

    @staticmethod
    def _read(path: Path) -> str:
        return path.read_text(encoding="utf-8").strip() if path.is_file() else ""

    @staticmethod
    def _export_hash(path: Path) -> str:
        digest = hashlib.sha256()
        for item in sorted(
            (
                value for value in path.rglob("*")
                if value.is_file() and value.name != ".DS_Store"
            ),
            key=lambda value: str(value.relative_to(path)),
        ):
            relative = str(item.relative_to(path)).encode("utf-8")
            digest.update(len(relative).to_bytes(4, "big"))
            digest.update(relative)
            digest.update(item.read_bytes())
        return digest.hexdigest()

    @staticmethod
    def _slug(value: str) -> str:
        value = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
        return value[:96] or "untitled"
