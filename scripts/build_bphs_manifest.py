#!/usr/bin/env python3
"""Derive the BPHS (Santhanam) extraction manifest from the PDF itself.

Hand-authoring a 97-chapter manifest is how errors get in and stay in. This
script reads the book and writes the manifest, so re-running it is the check.

Two deliberate choices, both learned from the Uttara Kalamritam pass:

1. **Chapter locations come from the BODY, never the table of contents.** This
   book has two contents blocks (chapters 1-45 at PDF 2-5, chapters 46-97 at
   PDF 400+) and the first one has its page-number column flattened by the text
   extractor, exactly the failure that silently dropped a chapter last time.
   The body headings ("Chapter 4. Zodiacal Signs Described") are unambiguous,
   and the result self-validates: all 97 present, no gaps, pages strictly
   ascending. Any of those three failing means the parse broke, loudly.

2. **Every page is scored for text quality** and pages that fall below the
   prose threshold are listed per chapter as `vision_pages`. They are almost
   all charts and dasha tables — the text layer flattens their columns the same
   way it flattened the contents. Naming them up front means an extraction pass
   knows where reading the text layer is not good enough, instead of discovering
   it by producing garbage.

The source book is not in the repo (the knowledge-base folder is untracked), so
pass its path when running from a worktree:

Usage:  python scripts/build_bphs_manifest.py [path/to/BPHS-Santhanam-Vol-1.pdf]
          > docs/kb_manifests/bphs_santhanam.json
"""
import json
import re
import subprocess
import statistics
import sys
from pathlib import Path

PDF = Path("Astro Space Knowledge Base/PDFs/BPHS-Santhanam-Vol-1.pdf")
DICT = Path("/usr/share/dict/words")

# Domain vocabulary a general English dictionary does not carry. Without this the
# score punishes the book for being about astrology.
DOMAIN = set("""native planet planets lord lords sign signs house houses moon sun mars mercury
jupiter venus saturn rahu ketu dasha dasa dashas bhava bhavas lagna navamsa navamsha rashi rasi
yoga yogas malefic malefics benefic benefics astrology horoscope aspects aspecting conjunction
retrograde exaltation debilitation karaka parasara parashara maitreya shloka verse chapter effects
wealth ascendant antardasha varga vargas amsa amsas trine trines kendra kona nakshatra nakshatras
ch st nd rd th etc viz""".split())

PROSE_MIN_TOKENS = 20      # fewer than this and the page is a table or a plate
PROSE_ACCURACY_FLOOR = 60  # below this the text layer is not trustworthy prose


def page_texts(pdf: Path) -> list[str]:
    out = subprocess.run(["pdftotext", str(pdf), "-"], capture_output=True, text=True)
    if out.returncode != 0:
        sys.exit(f"pdftotext failed on {pdf}: {out.stderr.strip()}")
    return out.stdout.split("\f")


def accuracy(text: str, words: set[str]) -> float | None:
    """Percent of alphabetic tokens that are real words. None = not prose."""
    toks = [t.lower() for t in re.findall(r"[A-Za-z]{2,}", text)]
    if len(toks) < PROSE_MIN_TOKENS:
        return None
    ok = sum(1 for t in toks if t in words or t in DOMAIN or t.rstrip("s") in words)
    return 100.0 * ok / len(toks)


def find_chapters(pages: list[str]) -> dict[int, tuple[int, str]]:
    """Chapter number -> (1-based PDF page, title), located from body headings."""
    pat = re.compile(r"^\s*Chapter\s+(\d{1,3})\s*\.\s*(.*)$", re.M)
    found: dict[int, tuple[int, str]] = {}
    for idx, page in enumerate(pages):
        for m in pat.finditer(page):
            num = int(m.group(1))
            if not (1 <= num <= 97) or num in found:
                continue
            # Long titles wrap: "Chapter 64. Effects of Antardasa in" / "the
            # Kalachakra Dasha". Take the rest of the heading line, then keep
            # absorbing following lines while they still look like title text —
            # stopping at Devanagari (the verse) or at a numbered translation.
            # A wrapped title always breaks mid-phrase, leaving a dangling
            # preposition or article. Requiring that is what stops the scan from
            # swallowing the sub-heading that follows a complete title —
            # chapters 54 and 55 sit directly above "Effects of the Antardasa
            # of ..." and were absorbing it.
            # "&" needs to sit outside the \b group — there is no word boundary
            # between a space and an ampersand, so \b& never matches.
            DANGLING = r"(\b(and|or|of|in|on|the|a|an|for|from|to|with|at|by|its)|&)$"
            parts = [m.group(2).strip()]
            for line in page[m.end():].splitlines():
                line = line.strip()
                if not line:
                    continue
                # A continuation either leaves the previous line dangling
                # ("...Antardasa in" / "the Kalachakra Dasha") or begins with the
                # dangling word itself ("Effects of the Antardasa" / "of the
                # Moon"). A genuine new heading starts with a capitalised word
                # that is neither.
                continues = (re.search(DANGLING, parts[-1], re.I)
                             or re.match(r"^(of|in|the|and|to|for|from|with|an?)\b", line, re.I))
                if not continues:
                    break
                if re.search(r"[ऀ-ॿ]", line) or re.match(r"^\d", line) or len(line) > 60:
                    break
                parts.append(line)
                if len(parts) >= 3:
                    break
            title = re.sub(r"[ऀ-ॿ].*$", "", " ".join(parts)).strip(" .:")
            found[num] = (idx + 1, " ".join(title.split())[:100])
    return found


def main() -> None:
    pdf = Path(sys.argv[1]) if len(sys.argv) > 1 else PDF
    if not pdf.exists():
        sys.exit(f"missing {pdf} — pass the book's path, or run from a checkout that has it")
    words = {w.strip().lower() for w in DICT.read_text(errors="ignore").splitlines()}
    pages = page_texts(pdf)
    chapters = find_chapters(pages)

    # The three invariants. A manifest built on a broken parse is worse than none.
    problems = []
    if len(chapters) != 97:
        problems.append(f"located {len(chapters)} chapters, expected 97")
    gaps = [n for n in range(1, 98) if n not in chapters]
    if gaps:
        problems.append(f"missing chapter numbers {gaps}")
    starts = [chapters[n][0] for n in sorted(chapters)]
    if starts != sorted(starts):
        problems.append("chapter start pages are not ascending — headings matched out of order")
    if problems:
        sys.exit("REFUSING to emit a manifest:\n  - " + "\n  - ".join(problems))

    empty = [n for n, (_, t) in chapters.items() if not t]
    if empty:
        sys.exit(f"REFUSING to emit a manifest:\n  - chapters with no title parsed: {empty}")

    # Independent check: the contents blocks are untrustworthy for PAGE numbers
    # (flattened columns) but their TITLES are fine, so they make a good second
    # opinion on whether the body headings were read correctly. Reported, not
    # enforced — a legitimate wording difference should not block a manifest.
    toc_titles: dict[int, str] = {}
    for m in re.finditer(r"^\s*(\d{1,3})\.\s+([A-Za-z][^\n]{4,80})$", "\n".join(pages[:5] + pages[399:411]), re.M):
        n = int(m.group(1))
        if 1 <= n <= 97:
            # Contents lines often trail their page number: "... Dasha System 494".
            toc_titles.setdefault(n, " ".join(re.sub(r"\s+\d{1,3}\s*$", "", m.group(2)).split()))

    def norm(s: str) -> set[str]:
        return {w for w in re.findall(r"[a-z]{4,}", s.lower())}

    agree = [n for n, t in toc_titles.items()
             if n in chapters and norm(t) & norm(chapters[n][1])]
    disagree = sorted(set(toc_titles) - set(agree))

    scores = {i + 1: accuracy(p, words) for i, p in enumerate(pages)}
    prose = [s for s in scores.values() if s is not None]

    # Titles come from the contents, which prints them complete on one logical
    # line; body headings wrap across up to four lines and are awkward to
    # reassemble (chapter 52 is "Effects of the Antardasa / of Sun according to
    # Vimshottari / Dasha System"). The body heading is kept as the check that
    # the right title was taken. This is not a retreat from "positions come from
    # the body" — PAGE numbers in the contents are the untrustworthy part, and
    # they are still ignored entirely.
    out_chapters = []
    ordered = sorted(chapters)
    for pos, num in enumerate(ordered):
        first, body_title = chapters[num]
        title = toc_titles.get(num) if num in agree else None
        title_source = "contents (cross-checked against body heading)" if title else "body heading"
        title = title or body_title
        last = chapters[ordered[pos + 1]][0] - 1 if pos + 1 < len(ordered) else len(pages) - 1
        rng = range(first, last + 1)
        vision = [p for p in rng if scores.get(p) is None or scores[p] < PROSE_ACCURACY_FLOOR]
        ch_prose = [scores[p] for p in rng if scores.get(p) is not None]
        out_chapters.append({
            "chapter": num,
            "title": title,
            "title_source": title_source,
            "body_heading": body_title,
            "first_pdf_page": first,
            "last_pdf_page": last,
            "pages": last - first + 1,
            "median_text_accuracy": round(statistics.median(ch_prose), 1) if ch_prose else None,
            "vision_pages": vision,
        })

    manifest = {
        "book": "Brihat Parasara Hora Shastra",
        "attributed_to": "Maharishi Parasara",
        "translator": "R. Santhanam",
        "source_file": str(PDF),  # canonical repo-relative location, not the path passed in
        "pdf_pages": len(pages) - 1,
        "chapters_total": len(out_chapters),
        "filename_note": (
            "The file is named 'Vol-1' but contains the COMPLETE text, chapters 1-97. "
            "It carries two contents blocks — chapters 1-45 at PDF 2-5 and chapters 46-97 "
            "at PDF 400 — which is what makes it look like a part-volume. Chapter 97 "
            "('Conclusion') is present in the body. No second volume is needed from this "
            "translation."
        ),
        "extraction_method": (
            "text layer, verified before use. Chapter positions are located from body "
            "headings, never from the contents blocks."
        ),
        "why_text_layer_is_trusted_here": (
            f"Median English accuracy {statistics.median(prose):.1f}% across {len(prose)} prose "
            "pages, measured against a dictionary. This is the first book in the corpus to clear "
            "the bar: the earlier Sharma scan of this same text had NO text layer at all, which "
            "is why documents generated from it were fabricated — there was nothing to ground on."
        ),
        "devanagari_caveat": (
            "The Sanskrit renders as mojibake (a font-encoding problem, not OCR). Only the "
            "English translation is extractable, and it is what we read. Verse numbers appear "
            "in the English lines ('39. If Chapa is in the 2nd...'), so verses remain addressable."
        ),
        "title_crosscheck": {
            "titles_found_in_contents": len(toc_titles),
            "agree_with_body_heading": len(agree),
            "no_overlap": disagree,
            "note": (
                "Body headings checked against the contents blocks as a second opinion. "
                "Chapter positions still come from the body alone; this only confirms the "
                "right heading was read. Entries under `no_overlap` share no significant "
                "word with the contents title and are worth an eye."
            ),
        },
        "quality": {
            "prose_pages": len(prose),
            "non_prose_pages": len(scores) - len(prose),
            "median_accuracy": round(statistics.median(prose), 1),
            "pages_below_floor": sum(1 for s in prose if s < PROSE_ACCURACY_FLOOR),
            "accuracy_floor": PROSE_ACCURACY_FLOOR,
        },
        "vision_pages_note": (
            "`vision_pages` are charts, speculums and dasha tables whose columns the text layer "
            "flattens. Read those as images; the rest can be read as text."
        ),
        "chapters": out_chapters,
    }
    print(json.dumps(manifest, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
