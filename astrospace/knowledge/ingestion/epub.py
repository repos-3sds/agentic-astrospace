from __future__ import annotations

import hashlib
import posixpath
import re
import zipfile
from html.parser import HTMLParser
from pathlib import Path
from xml.etree import ElementTree as ET

from .models import EpubBook, EpubSection, TextBlock

_BLOCK_TAGS = {
    "p", "h1", "h2", "h3", "h4", "h5", "h6", "li", "blockquote",
    "pre", "figcaption", "td", "th",
}
_ACCURACY_RE = re.compile(r"estimated to be only\s+([0-9.]+)%\s+accurate", re.I)
_PAGE_RE = re.compile(r"(?:page[_\s-]*)(\d+)", re.I)


def _sha256(data: bytes | str) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _clean(text: str) -> str:
    text = text.replace("\xa0", " ")
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r"\s*\n\s*", "\n", text)
    return text.strip()


class _BlockParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.in_body = False
        self.ignored_depth = 0
        self.current_tag: str | None = None
        self.parts: list[str] = []
        self.blocks: list[tuple[str, str]] = []
        self.title_parts: list[str] = []
        self.in_title = False

    def handle_starttag(self, tag: str, attrs):
        tag = tag.lower()
        if tag == "title":
            self.in_title = True
        if tag == "body":
            self.in_body = True
        if tag in {"script", "style", "svg"}:
            self.ignored_depth += 1
        if not self.in_body or self.ignored_depth:
            return
        if tag in _BLOCK_TAGS:
            self._finish()
            self.current_tag = tag
        elif tag == "br" and self.current_tag:
            self.parts.append("\n")

    def handle_endtag(self, tag: str):
        tag = tag.lower()
        if tag == "title":
            self.in_title = False
        if tag in {"script", "style", "svg"} and self.ignored_depth:
            self.ignored_depth -= 1
        if tag == self.current_tag:
            self._finish()
        if tag == "body":
            self._finish()
            self.in_body = False

    def handle_data(self, data: str):
        if self.in_title:
            self.title_parts.append(data)
        if self.in_body and not self.ignored_depth:
            if self.current_tag:
                self.parts.append(data)

    def close(self):
        super().close()
        self._finish()

    def _finish(self):
        if self.current_tag:
            text = _clean("".join(self.parts))
            if text:
                self.blocks.append((self.current_tag, text))
        self.current_tag = None
        self.parts = []


class EpubExtractor:
    """Extract source-derived text blocks in EPUB spine order."""

    parser_version = "epub-stdlib-v1"

    def extract(self, path: str | Path, *, source_key: str | None = None,
                start_section: int = 0,
                max_sections: int | None = None) -> EpubBook:
        path = Path(path)
        payload = path.read_bytes()
        with zipfile.ZipFile(path) as archive:
            opf_path = self._opf_path(archive)
            metadata, spine = self._package(archive, opf_path)
            indexed_spine = list(enumerate(spine))[start_section:]
            if max_sections is not None:
                indexed_spine = indexed_spine[:max_sections]
            sections = [
                self._section(archive, opf_path, href, ordinal)
                for ordinal, href in indexed_spine
            ]
        sections = [section for section in sections if section.blocks]
        return EpubBook(
            source_key=source_key or self._slug(metadata.get("title") or path.stem),
            title=metadata.get("title") or path.stem,
            author=metadata.get("creator"),
            language=metadata.get("language"),
            identifier=metadata.get("identifier"),
            sha256=_sha256(payload),
            sections=tuple(sections),
        )

    @staticmethod
    def _opf_path(archive: zipfile.ZipFile) -> str:
        root = ET.fromstring(archive.read("META-INF/container.xml"))
        node = root.find(".//{*}rootfile")
        if node is None or not node.attrib.get("full-path"):
            raise ValueError("EPUB container does not declare an OPF package")
        return node.attrib["full-path"]

    @staticmethod
    def _package(archive: zipfile.ZipFile, opf_path: str) -> tuple[dict, list[str]]:
        root = ET.fromstring(archive.read(opf_path))
        metadata_node = root.find("{*}metadata")
        metadata = {}
        for key in ("title", "creator", "language", "identifier"):
            node = metadata_node.find(f"{{*}}{key}") if metadata_node is not None else None
            metadata[key] = _clean(node.text or "") if node is not None else None
        manifest = {
            item.attrib["id"]: item.attrib
            for item in root.findall(".//{*}manifest/{*}item")
        }
        spine = []
        for itemref in root.findall(".//{*}spine/{*}itemref"):
            item = manifest.get(itemref.attrib.get("idref", ""))
            if not item:
                continue
            if item.get("media-type") not in {"application/xhtml+xml", "text/html"}:
                continue
            properties = set(item.get("properties", "").split())
            if properties & {"nav", "cover-image"}:
                continue
            href = item.get("href")
            if href:
                spine.append(href)
        return metadata, spine

    def _section(self, archive: zipfile.ZipFile, opf_path: str,
                 href: str, ordinal: int) -> EpubSection:
        member = posixpath.normpath(posixpath.join(posixpath.dirname(opf_path), href))
        raw = archive.read(member)
        parser = _BlockParser()
        parser.feed(raw.decode("utf-8", errors="replace"))
        parser.close()
        confidence = None
        source_blocks = []
        for tag, text in parser.blocks:
            match = _ACCURACY_RE.search(text)
            if match:
                confidence = float(match.group(1)) / 100.0
                continue
            source_blocks.append((tag, text))
        title = _clean("".join(parser.title_parts)) or None
        page_match = _PAGE_RE.search(title or href)
        page_label = page_match.group(1) if page_match else None
        blocks = tuple(
            TextBlock(
                id=f"s{ordinal:04d}-b{block_ordinal:04d}",
                section_ordinal=ordinal,
                block_ordinal=block_ordinal,
                href=href,
                tag=tag,
                text=text,
                page_label=page_label,
                extraction_confidence=confidence,
            )
            for block_ordinal, (tag, text) in enumerate(source_blocks)
        )
        exact_text = "\n\n".join(block.text for block in blocks)
        return EpubSection(
            ordinal=ordinal,
            href=href,
            title=title,
            page_label=page_label,
            blocks=blocks,
            exact_text=exact_text,
            text_sha256=_sha256(exact_text),
            raw_xhtml_sha256=_sha256(raw),
            extraction_confidence=confidence,
        )

    @staticmethod
    def _slug(value: str) -> str:
        value = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
        return value[:96] or "untitled"
