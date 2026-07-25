from collections import Counter

from astrospace.knowledge.ingestion.scope import classify_retrieval_scope


def _counts(source_key: str, chunk_count: int) -> Counter:
    return Counter(
        classify_retrieval_scope(source_key, ordinal, "", "").scope
        for ordinal in range(chunk_count)
    )


def test_curated_edition_scope_counts():
    assert _counts("brihat-jataka", 359) == {
        "core": 343,
        "editorial": 10,
        "navigation": 5,
        "publishing": 1,
    }
    assert _counts("brihat-parasara-hora-sastra-volume-1", 363) == {
        "core": 358,
        "navigation": 3,
        "publishing": 1,
        "editorial": 1,
    }
    assert _counts("phaladeepika-mantreswara", 310) == {
        "core": 157,
        "navigation": 152,
        "publishing": 1,
    }
    assert _counts("saravali-kalyana-varma", 200) == {
        "core": 182,
        "publishing": 9,
        "navigation": 7,
        "editorial": 2,
    }
    assert _counts("uttara-kalamritam", 206) == {
        "core": 159,
        "out_of_domain": 37,
        "navigation": 8,
        "publishing": 2,
    }


def test_mixed_boundaries_keep_astrology_side_retrievable():
    assert classify_retrieval_scope(
        "phaladeepika-mantreswara", 23, "ADHYAYA 27", "mixed boundary",
    ).scope == "core"
    assert classify_retrieval_scope(
        "phaladeepika-mantreswara", 180, "FINIS", "index begins",
    ).scope == "navigation"
    assert classify_retrieval_scope(
        "uttara-kalamritam", 149, "Notes", "end of first kanda",
    ).scope == "core"
    assert classify_retrieval_scope(
        "uttara-kalamritam", 150, "Notes", "ritual section",
    ).scope == "out_of_domain"
    assert classify_retrieval_scope(
        "uttara-kalamritam", 188, "Notes", "astrology resumes",
    ).scope == "core"


def test_unknown_sources_only_exclude_strong_structural_markers():
    assert classify_retrieval_scope(
        "unknown-book", 4, "CONTENTS", "Chapter I 10",
    ).scope == "navigation"
    assert classify_retrieval_scope(
        "unknown-book", 5, "PREFACE", "Editorial history",
    ).scope == "editorial"
    assert classify_retrieval_scope(
        "unknown-book", 6, "Planetary strengths", "A rule and explanation",
    ).scope == "core"
