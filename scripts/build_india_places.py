"""
Build the village-level populated-places dataset for all of India from the
GeoNames dump, for the city search/lookup in astrospace/core/cities.py.

Usage:
    python scripts/build_india_places.py IN.txt admin1CodesASCII.txt admin2Codes.txt

Data source: https://download.geonames.org/export/dump/ (IN.zip,
admin1CodesASCII.txt, admin2Codes.txt). GeoNames is licensed CC-BY 4.0 —
attribution: GeoNames (geonames.org).

Output: astrospace/core/data/india_places.tsv.gz. The first line is
"# " + JSON metadata, including `districts`, a list of [district, state];
every other line is one place:

    name <TAB> lat <TAB> lng <TAB> district index <TAB> population <TAB> alternates

with alternates joined by "|". Rows are population-sorted so search ranks
bigger towns first. All of India is IANA Asia/Kolkata. The format is flat so
the server can stream it into compact arrays: ~15x the old AP/Telangana
layer would not fit a 1 GiB instance as Python lists.

India is not in COUNTRIES in scripts/build_world_places.py, so a town is not
listed twice.
"""
from __future__ import annotations

import gzip
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from build_world_places import _REGION_OVERRIDES  # noqa: E402
from astrospace.core.cities import _normalize  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "astrospace" / "core" / "data" / "india_places.tsv.gz"
_ALT = re.compile(r"[A-Za-z .'-]+")
# GeoNames feature codes of capitals and administrative seats, most senior
# first; any other populated place ranks after them.
_SEAT_RANK = {code: rank for rank, code in enumerate(
    ["PPLC", "PPLA", "PPLA2", "PPLA3", "PPLA4", "PPLA5"])}
# An unknown admin1 code with at least this many places is a new state.
_NEW_STATE_MIN = 100


def load_states(admin1_path: Path) -> dict[str, str]:
    """GeoNames admin1 code -> state name, with the same renames the
    country-level layer uses (Delhi, not "NCT"), so a profile saved as
    "Aurangabad, Bihar" from that layer still resolves here."""
    states: dict[str, str] = {}
    for line in admin1_path.read_text(encoding="utf-8").splitlines():
        parts = line.split("\t")
        if len(parts) >= 2 and parts[0].startswith("IN."):
            states[parts[0][3:]] = parts[1]
    states.update(_REGION_OVERRIDES["IN"])
    return states


def load_districts(admin2_path: Path) -> dict[str, str]:
    districts: dict[str, str] = {}
    for line in admin2_path.read_text(encoding="utf-8").splitlines():
        parts = line.split("\t")
        if len(parts) >= 2 and parts[0].startswith("IN."):
            districts[parts[0]] = parts[1]
    return districts


def _clean(text: str) -> str:
    # Tabs, newlines and "|" carry the file format; commas carry the
    # "Name, District" form profiles are saved in.
    return re.sub(r"\s+", " ", re.sub(r"[\t\n|,]", " ", text)).strip()


def build(in_txt: Path, admin1_path: Path, admin2_path: Path) -> tuple[list[list], list[list[str]]]:
    states = load_states(admin1_path)
    districts = load_districts(admin2_path)
    best: dict[tuple[str, str, str], list] = {}
    unnamed: dict[str, int] = {}
    for line in in_txt.open(encoding="utf-8"):
        parts = line.rstrip("\n").split("\t")
        if len(parts) < 18 or parts[6] != "P" or parts[8] != "IN":
            continue
        name = _clean(parts[1])
        admin1 = parts[10]
        state = states.get(admin1)
        if not name:
            continue
        if not state:
            unnamed[admin1] = unnamed.get(admin1, 0) + 1
            continue
        district = _clean(districts.get(f"IN.{admin1}.{parts[11]}", ""))
        population = int(parts[14] or 0)
        # ASCII alternate spellings (transliteration variants like
        # Bhainsa/Bhaisa, Sangareddy/Sangareddi) — essential for lookup.
        seen_alt = {name.lower()}
        alternates = []
        for alt in parts[3].split(","):
            alt = alt.strip()
            if alt and alt.isascii() and alt.lower() not in seen_alt and _ALT.fullmatch(alt):
                seen_alt.add(alt.lower())
                alternates.append(alt)
            if len(alternates) >= 8:
                break
        row = [name, round(float(parts[4]), 4), round(float(parts[5]), 4),
               (district, state), population, alternates, _SEAT_RANK.get(parts[7], len(_SEAT_RANK))]
        # Same name within the same district, diacritics aside (Guntūrpalli,
        # Gunturpalli): keep the more populous record, since both would save
        # as the same "Name, District"; at equal population (most villages
        # are 0) the administrative seat.
        key = (_normalize(name), _normalize(district), state)
        if key not in best or (-population, row[6]) < (-best[key][4], best[key][6]):
            best[key] = row
    # A new admin1 code (a state split or a renamed UT) needs a name. A
    # handful of records carry no state at all ("", "00") or a retired code
    # (one Punjab hamlet under "04" in the 2026-10 dump); a label we cannot
    # name is worse than leaving them out.
    new_codes = sorted(code for code, n in unnamed.items() if n >= _NEW_STATE_MIN)
    if new_codes:
        raise SystemExit(f"no state name for admin1 codes {new_codes}; "
                         "add them to _REGION_OVERRIDES['IN'] in build_world_places.py")
    if unnamed:
        print(f"skipped {sum(unnamed.values())} places with no state "
              f"(admin1 {dict(sorted(unnamed.items()))})")
    # A seat before same-sized villages, so "Nautan, Bihar" stays the block
    # town the country-level layer saved it as, not a hamlet of that name.
    rows = sorted(best.values(), key=lambda r: (-r[4], r[6], r[0]))
    table: dict[tuple[str, str], int] = {}
    for row in rows:
        row[3] = table.setdefault(row[3], len(table))
    return rows, [list(pair) for pair in table]


def main() -> None:
    if len(sys.argv) != 4:
        raise SystemExit(__doc__)
    rows, districts = build(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))
    meta = {
        "source": "GeoNames (geonames.org), CC-BY 4.0",
        "timezone": "Asia/Kolkata",
        "count": len(rows),
        "districts": districts,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(OUT, "wt", encoding="utf-8") as fh:
        fh.write("# " + json.dumps(meta, ensure_ascii=False, separators=(",", ":")) + "\n")
        for name, lat, lng, district, population, alternates, _ in rows:
            fh.write(f"{name}\t{lat}\t{lng}\t{district}\t{population}\t{'|'.join(alternates)}\n")
    states = {state for _, state in districts}
    print(f"wrote {len(rows)} places in {len(districts)} districts of {len(states)} "
          f"states -> {OUT} ({OUT.stat().st_size // 1024} KiB)")


if __name__ == "__main__":
    main()
