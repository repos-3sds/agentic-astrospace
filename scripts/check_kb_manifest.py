#!/usr/bin/env python3
"""Completeness gate for a KB extraction manifest.

A manifest is the claim "this is everything the book contains". That claim has
to be checkable, or it is just a hope — and the first attempt at this book's
manifest silently lost Chapter III and returned zero entries for IV and V, with
no error at all. These checks exist so that failure mode is loud.

Usage:  python scripts/check_kb_manifest.py docs/kb_manifests/<book>.json
Exit 0 = manifest may be used. Exit 1 = rejected, do not extract against it.
"""
import json, re, sys

ROMAN = {"I":1,"II":2,"III":3,"IV":4,"V":5,"VI":6,"VII":7,"VIII":8,"IX":9,"X":10,
         "XI":11,"XII":12,"XIII":13,"XIV":14,"XV":15,"XVI":16,"XVII":17,"XVIII":18,
         "XIX":19,"XX":20}


def check_flat(m: dict) -> list[str]:
    """Books with a flat chapter list and no kanda level (e.g. BPHS).

    These manifests are script-generated from the book rather than read by hand,
    so the generator already refuses to emit a broken one. This re-checks the
    result independently: a generator that is wrong about its own output is
    exactly the thing a gate exists to catch.
    """
    problems: list[str] = []
    chapters = m["chapters"]
    if not chapters:
        return ["no chapters at all"]

    nums = [c["chapter"] for c in chapters]
    expected = list(range(nums[0], nums[0] + len(nums)))
    if nums != expected:
        missing = sorted(set(expected) - set(nums))
        problems.append(f"chapter numbers are not contiguous (missing {missing}) — a chapter was dropped")

    floor = m.get("quality", {}).get("accuracy_floor", 60)
    median = m.get("quality", {}).get("median_accuracy")
    if median is None:
        problems.append("no measured text quality — a manifest may not assert a book is readable without checking")
    elif median < floor:
        problems.append(
            f"median text accuracy {median}% is below the {floor}% floor — this book's text layer "
            f"is not trustworthy prose and must be read as images, not extracted"
        )

    for c in chapters:
        where = f"ch {c['chapter']}"
        if not c.get("title", "").strip():
            problems.append(f"{where}: empty title")
        first, last = c.get("first_pdf_page"), c.get("last_pdf_page")
        if not (isinstance(first, int) and isinstance(last, int)):
            problems.append(f"{where}: missing page bounds")
            continue
        if last < first:
            problems.append(f"{where}: page range runs backwards ({first}-{last})")
        stray = [p for p in c.get("vision_pages", []) if not (first <= p <= last)]
        if stray:
            problems.append(f"{where}: vision_pages {stray} fall outside the chapter's own range")

    # Chapters must tile the book: consecutive, no gaps, no overlaps.
    for a, b in zip(chapters, chapters[1:]):
        if a.get("last_pdf_page") is None or b.get("first_pdf_page") is None:
            continue
        if a["last_pdf_page"] + 1 != b["first_pdf_page"]:
            problems.append(
                f"ch {a['chapter']} ends p{a['last_pdf_page']} but ch {b['chapter']} starts "
                f"p{b['first_pdf_page']} — chapters must tile the book with no gap or overlap"
            )
    return problems


def check(path: str) -> list[str]:
    m = json.load(open(path, encoding="utf-8"))
    problems: list[str] = []

    # Two shapes in the corpus: kanda/chapter/shloka books, and flat-chapter books.
    if "kandas" not in m:
        return check_flat(m)

    if m.get("toc_pages_pending"):
        problems.append(
            f"TOC pages {m['toc_pages_pending']} are unread — the manifest cannot "
            f"claim completeness while part of the contents has never been looked at"
        )

    chapters = [(k["kanda"], c) for k in m["kandas"] for c in k["chapters"]]
    if not chapters:
        problems.append("no chapters at all")
        return problems

    # Pages absent from the scan are declared once at book level. Every chapter
    # whose range covers one has to say so itself, because that is where anyone
    # extracting will actually be looking — a book-level footnote gets skipped.
    absent = set(m.get("missing_printed_pages", []))
    for kanda_id, c in chapters:
        first, last = c.get("first_page"), c.get("last_page")
        if not (isinstance(first, int) and isinstance(last, int)):
            continue
        overlap = sorted(p for p in absent if first <= p <= last)
        declared = sorted(c.get("missing_pages", []))
        if overlap != declared:
            problems.append(
                f"kanda {kanda_id} ch {c['chapter']}: spans missing printed page(s) {overlap} "
                f"but declares {declared or 'none'} — a chapter with holes must name them"
            )

    # Chapter numbers contiguous within each kanda: a gap is a lost chapter.
    for kanda in m["kandas"]:
        nums = [ROMAN.get(c["chapter"], -1) for c in kanda["chapters"]]
        if -1 in nums:
            problems.append(f"kanda {kanda['kanda']}: unparseable chapter numeral")
        expected = list(range(nums[0], nums[0] + len(nums)))
        if nums != expected:
            missing = sorted(set(expected) - set(nums))
            problems.append(
                f"kanda {kanda['kanda']}: chapter numbers {nums} are not contiguous "
                f"(missing {missing}) — a gap means a chapter was dropped"
            )

    for kanda_id, c in chapters:
        where = f"kanda {kanda_id} ch {c['chapter']}"
        # A chapter whose own TOC listing stops short is incomplete no matter how
        # well-formed its entries are. Documenting the truncation is not the same
        # as closing it — the missing shlokas have to be read off the body pages.
        if c.get("toc_truncated_after"):
            t = c["toc_truncated_after"]
            problems.append(
                f"{where}: TOC stops at shloka {t.get('last_toc_shloka')} (p{t.get('last_toc_page')}) "
                f"but the chapter runs to p{c.get('last_page')} — enumerate the rest from the "
                f"body pages, or this manifest is complete only where the printed TOC was"
            )
        # Zero entries is the exact silent failure this gate was written for.
        if not c.get("entries"):
            problems.append(f"{where}: zero entries — the parse dropped this chapter's contents")
            continue
        # Page numbers must not run backwards within a chapter.
        pages = [e["page"] for e in c["entries"] if isinstance(e.get("page"), int)]
        if pages != sorted(pages):
            problems.append(f"{where}: entry pages are not ascending — column misalignment")
        if pages and c.get("first_page") and pages[0] != c["first_page"]:
            problems.append(f"{where}: first entry is p{pages[0]} but chapter starts at p{c['first_page']}")
        # Shloka ranges must be parseable and non-decreasing.
        starts = []
        for e in c["entries"]:
            mt = re.match(r"^(\d+)", str(e.get("shlokas", "")))
            if not mt:
                problems.append(f"{where}: unparseable shloka ref {e.get('shlokas')!r}")
            else:
                starts.append(int(mt.group(1)))
        if starts != sorted(starts):
            problems.append(f"{where}: shloka numbers run backwards — entries out of order")

    # Chapters must tile the book without overlap.
    for (k1, a), (k2, b) in zip(chapters, chapters[1:]):
        if a.get("last_page") and b.get("first_page") and a["last_page"] > b["first_page"]:
            problems.append(
                f"ch {a['chapter']} ends p{a['last_page']} after ch {b['chapter']} "
                f"starts p{b['first_page']} — overlapping ranges"
            )
    return problems


if __name__ == "__main__":
    path = sys.argv[1]
    found = check(path)
    if not found:
        print(f"PASS  {path}")
        sys.exit(0)
    print(f"REJECTED  {path}")
    for p in found:
        print(f"  - {p}")
    sys.exit(1)
