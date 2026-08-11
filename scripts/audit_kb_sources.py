#!/usr/bin/env python3
"""Measure every book in the knowledge base and report whether it is readable.

This exists because the corpus has now been described from memory twice and been
wrong both times — most recently "Sharma Vol 2 tested clean", which has no
extractable text whatsoever. Numbers in docs go stale and get misquoted; a
command does not. Re-run this instead of trusting the table.

What it measures, per file:

  * **words**      total alphabetic tokens the text layer yields. Zero means the
                   file is an image scan with no text layer at all — a different
                   failure from bad OCR, and the one that produced fabricated
                   documents, because there was nothing to ground against.
  * **accuracy**   median percent of tokens that are real dictionary words,
                   across pages with enough text to judge. Low means OCR ran but
                   produced mush.
  * **verdict**    what you can actually do with the file.

A file can be a perfectly good scan and still score zero here. That is not a
judgement on the book — it means read it as images, the way Uttara Kalamritam
was read. `vision` in the verdict column means exactly that.

Usage:  python scripts/audit_kb_sources.py ["Astro Space Knowledge Base"] [--json]
"""
import json
import html
import re
import statistics
import subprocess
import sys
import zipfile
from pathlib import Path

DICT = Path("/usr/share/dict/words")
DOMAIN = set("""native planet planets lord lords sign signs house houses moon sun mars mercury
jupiter venus saturn rahu ketu dasha dasa bhava bhavas lagna navamsa rashi rasi yoga yogas
malefic malefics benefic benefics astrology horoscope aspects conjunction retrograde exaltation
debilitation karaka parasara parashara maitreya shloka verse chapter effects wealth ascendant
nakshatra nakshatras varga vargas amsa kendra kona ch st nd rd th etc viz""".split())

MIN_TOKENS = 20   # below this a page is a table, a plate, or blank
FLOOR = 60        # below this the text layer is not trustworthy prose


def score_pages(pages: list[str], words: set[str]) -> tuple[int, float | None, int]:
    """-> (total words, median accuracy over prose pages, prose page count)"""
    total, scores = 0, []
    for p in pages:
        toks = [t.lower() for t in re.findall(r"[A-Za-z]{2,}", p)]
        total += len(toks)
        if len(toks) < MIN_TOKENS:
            continue
        ok = sum(1 for t in toks if t in words or t in DOMAIN or t.rstrip("s") in words)
        scores.append(100.0 * ok / len(toks))
    return total, (statistics.median(scores) if scores else None), len(scores)


def pdf_pages(path: Path) -> list[str]:
    out = subprocess.run(["pdftotext", str(path), "-"], capture_output=True, text=True)
    return out.stdout.split("\f") if out.returncode == 0 else []


def epub_pages(path: Path) -> list[str]:
    try:
        z = zipfile.ZipFile(path)
    except zipfile.BadZipFile:
        return []
    out = []
    for n in z.namelist():
        if n.lower().endswith((".html", ".xhtml", ".htm")):
            raw = z.read(n).decode("utf-8", "ignore")
            out.append(html.unescape(re.sub(r"<[^>]+>", " ", raw)))
    return out


def verdict(total: int, median: float | None, pages: int) -> str:
    if total == 0:
        return "NO TEXT LAYER — vision only"
    if pages and total / max(pages, 1) < 40:
        return "near-empty text — vision only"
    if median is None:
        return "no prose pages — vision only"
    if median >= 85:
        return "READABLE — extract as text"
    if median >= FLOOR:
        return "marginal — spot-check before trusting"
    return "OCR mush — vision only"


def main() -> None:
    args = [a for a in sys.argv[1:] if a != "--json"]
    root = Path(args[0]) if args else Path("Astro Space Knowledge Base")
    if not root.exists():
        sys.exit(f"missing {root} — pass the knowledge-base folder path")
    words = {w.strip().lower() for w in DICT.read_text(errors="ignore").splitlines()}

    rows = []
    for f in sorted(root.rglob("*")):
        # The OCR-export folders are DIRECTORIES named "<book>.pdf" holding a
        # markdown.md — so a suffix test alone matches them and reports a real
        # book as empty. Check for a file explicitly.
        if not f.is_file():
            continue
        # Each export also carries a pages/page-N/markdown.md per page — useful
        # later for page-level citation, but 2000 rows of noise in an inventory.
        # Only the book-level export belongs here.
        if f.name == "markdown.md" and "pages" not in f.parts:
            # A Mistral OCR export of a book whose own text layer failed. These
            # are the highest-value files in the corpus and the easiest to miss:
            # they are buried one level down under a directory that looks like a
            # PDF.
            text = f.read_text(errors="ignore")
            pages = [text[i:i + 3000] for i in range(0, len(text), 3000)]
            total, median, prose = score_pages(pages, words)
            rows.append({
                "file": f"{f.parent.name}/markdown.md",
                "kind": "ocr-export",
                "size_mb": round(f.stat().st_size / 1e6, 1),
                "units": len(pages),
                "words": total,
                "median_accuracy": round(median, 1) if median is not None else None,
                "prose_pages": prose,
                "verdict": verdict(total, median, len(pages)),
            })
            continue
        if f.suffix.lower() not in (".pdf", ".epub"):
            continue
        pages = pdf_pages(f) if f.suffix.lower() == ".pdf" else epub_pages(f)
        total, median, prose = score_pages(pages, words)
        rows.append({
            "file": str(f.relative_to(root)),
            "kind": f.suffix.lower().lstrip("."),
            "size_mb": round(f.stat().st_size / 1e6, 1),
            "units": len(pages),
            "words": total,
            "median_accuracy": round(median, 1) if median is not None else None,
            "prose_pages": prose,
            "verdict": verdict(total, median, len(pages)),
        })

    if "--json" in sys.argv:
        print(json.dumps(rows, indent=2))
        return

    w = max((len(r["file"]) for r in rows), default=10)
    print(f"{'file':{w}}  {'MB':>5}  {'units':>5}  {'words':>8}  {'acc':>6}  verdict")
    print("-" * (w + 46))
    for r in rows:
        acc = f"{r['median_accuracy']}%" if r["median_accuracy"] is not None else "—"
        print(f"{r['file']:{w}}  {r['size_mb']:5}  {r['units']:5}  {r['words']:8}  {acc:>6}  {r['verdict']}")


if __name__ == "__main__":
    main()
