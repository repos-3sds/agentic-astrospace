from __future__ import annotations

import hashlib
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

from .models import EpubBook, EpubSection, TextBlock


def _sha256(value: bytes | str) -> str:
    if isinstance(value, str):
        value = value.encode("utf-8")
    return hashlib.sha256(value).hexdigest()


class PdfExtractor:
    """Extract page-scoped text and scan evidence from a PDF."""

    parser_version = "pdf-poppler-v1"

    def extract(
        self,
        path: str | Path,
        *,
        source_key: str | None = None,
        start_section: int = 0,
        max_sections: int | None = None,
    ) -> EpubBook:
        self._require_poppler()
        path = Path(path)
        payload = path.read_bytes()
        metadata = self._metadata(path)
        total_pages = int(metadata.get("Pages") or 0)
        start_page = start_section + 1
        end_page = total_pages
        if max_sections is not None:
            end_page = min(end_page, start_page + max_sections - 1)
        key = source_key or self._slug(metadata.get("Title") or path.stem)
        title = metadata.get("Title") or key.replace("-", " ").title()
        sections = tuple(
            self._page(path, page_number, key)
            for page_number in range(start_page, end_page + 1)
        )
        return EpubBook(
            source_key=key,
            title=title,
            author=metadata.get("Author"),
            language=None,
            identifier=None,
            sha256=_sha256(payload),
            sections=sections,
            file_type="pdf",
        )

    def _page(self, path: Path, page_number: int, source_key: str) -> EpubSection:
        text = self._page_text(path, page_number)
        paragraphs = self._paragraphs(text)
        blocks = tuple(
            TextBlock(
                id=f"p{page_number:04d}-b{ordinal:04d}",
                section_ordinal=page_number - 1,
                block_ordinal=ordinal,
                href=f"page:{page_number}",
                tag="p",
                text=paragraph,
                page_label=str(page_number),
            )
            for ordinal, paragraph in enumerate(paragraphs)
        )
        exact_text = "\n\n".join(paragraphs)
        image = self._page_image(path, page_number)
        image_path = f"pages/{source_key}/page-{page_number:04d}.jpg"
        return EpubSection(
            ordinal=page_number - 1,
            href=f"page:{page_number}",
            title=f"Page {page_number}",
            page_label=str(page_number),
            blocks=blocks,
            exact_text=exact_text,
            text_sha256=_sha256(exact_text),
            raw_xhtml_sha256=_sha256(image),
            page_image=image,
            page_image_path=image_path,
            page_image_sha256=_sha256(image),
            extraction_method="pdf_text_layer",
        )

    @staticmethod
    def _page_text(path: Path, page_number: int) -> str:
        result = subprocess.run(
            [
                "pdftotext", "-f", str(page_number), "-l", str(page_number),
                "-layout", "-enc", "UTF-8", str(path), "-",
            ],
            check=True,
            capture_output=True,
        )
        return result.stdout.decode("utf-8", errors="replace").replace("\f", "").strip()

    @staticmethod
    def _page_image(path: Path, page_number: int) -> bytes:
        with tempfile.TemporaryDirectory(prefix="astrospace-pdf-") as directory:
            prefix = Path(directory) / "page"
            subprocess.run(
                [
                    "pdftoppm", "-f", str(page_number), "-l", str(page_number),
                    "-singlefile", "-jpeg", "-jpegopt", "quality=88",
                    "-r", "144", str(path), str(prefix),
                ],
                check=True,
                capture_output=True,
            )
            return prefix.with_suffix(".jpg").read_bytes()

    @staticmethod
    def _paragraphs(text: str) -> tuple[str, ...]:
        text = re.sub(r"[ \t]+\n", "\n", text)
        paragraphs = [
            re.sub(r"[ \t]+", " ", value).strip()
            for value in re.split(r"\n\s*\n", text)
            if value.strip()
        ]
        if len(paragraphs) == 1 and "\n" in paragraphs[0]:
            paragraphs = [
                value.strip()
                for value in paragraphs[0].splitlines()
                if value.strip()
            ]
        return tuple(paragraphs)

    @staticmethod
    def _metadata(path: Path) -> dict[str, str]:
        result = subprocess.run(
            ["pdfinfo", str(path)],
            check=True,
            capture_output=True,
            text=True,
        )
        return {
            key.strip(): value.strip()
            for line in result.stdout.splitlines()
            if ":" in line
            for key, value in [line.split(":", 1)]
        }

    @staticmethod
    def _require_poppler() -> None:
        missing = [
            command
            for command in ("pdfinfo", "pdftotext", "pdftoppm")
            if not shutil.which(command)
        ]
        if missing:
            raise RuntimeError(
                f"PDF ingestion requires Poppler commands: {', '.join(missing)}"
            )

    @staticmethod
    def _slug(value: str) -> str:
        value = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
        return value[:96] or "untitled"
