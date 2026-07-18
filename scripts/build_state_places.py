"""
Build a complete populated-places dataset for selected Indian states from the
GeoNames dump, for the city search/lookup in astrospace/core/cities.py.

Usage:
    python scripts/build_state_places.py /path/to/IN.txt /path/to/admin2Codes.txt

Data source: https://download.geonames.org/export/dump/ (IN.zip, admin2Codes.txt)
GeoNames is licensed CC-BY 4.0 — attribution: GeoNames (geonames.org).

Output: astrospace/core/data/state_places.json.gz — a JSON list of
[name, lat, lng, district, state_abbr, population], population-sorted so
search results rank larger towns first. All entries are IANA Asia/Kolkata.

Extend STATES to cover more states; keys are GeoNames admin1 codes for IN.
"""
from __future__ import annotations

import gzip
import json
import re
import sys
from pathlib import Path

STATES = {
    "02": "AP",  # Andhra Pradesh
    "40": "TS",  # Telangana
}

OUT = Path(__file__).resolve().parent.parent / "astrospace" / "core" / "data" / "state_places.json.gz"


def load_districts(admin2_path: Path) -> dict[str, str]:
    districts: dict[str, str] = {}
    for line in admin2_path.read_text(encoding="utf-8").splitlines():
        parts = line.split("\t")
        if len(parts) >= 2 and parts[0].startswith("IN."):
            districts[parts[0]] = parts[1]
    return districts


def build(in_txt: Path, admin2_path: Path) -> list[list]:
    districts = load_districts(admin2_path)
    best: dict[tuple[str, str], list] = {}
    for line in in_txt.open(encoding="utf-8"):
        parts = line.rstrip("\n").split("\t")
        if len(parts) < 18:
            continue
        fclass, country, admin1 = parts[6], parts[8], parts[10]
        if fclass != "P" or country != "IN" or admin1 not in STATES:
            continue
        name = parts[1].strip()
        if not name:
            continue
        lat, lng = float(parts[4]), float(parts[5])
        admin2 = parts[11]
        district = districts.get(f"IN.{admin1}.{admin2}", "")
        population = int(parts[14] or 0)
        # ASCII alternate spellings (transliteration variants like
        # Bhainsa/Bhaisa, Sangareddy/Sangareddi) — essential for lookup.
        seen_alt = {name.lower()}
        alternates = []
        for alt in parts[3].split(","):
            alt = alt.strip()
            if (alt and alt.isascii() and alt.lower() not in seen_alt
                    and re.fullmatch(r"[A-Za-z .'-]+", alt)):
                seen_alt.add(alt.lower())
                alternates.append(alt)
            if len(alternates) >= 8:
                break
        key = (name.lower(), district.lower())
        row = [name, round(lat, 4), round(lng, 4), district, STATES[admin1],
               population, alternates]
        # Same name within the same district: keep the more populous record.
        if key not in best or population > best[key][5]:
            best[key] = row
    return sorted(best.values(), key=lambda r: -r[5])


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    rows = build(Path(sys.argv[1]), Path(sys.argv[2]))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "source": "GeoNames (geonames.org), CC-BY 4.0",
        "states": STATES,
        "timezone": "Asia/Kolkata",
        "count": len(rows),
        "places": rows,
    }
    with gzip.open(OUT, "wt", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, separators=(",", ":"))
    print(f"wrote {len(rows)} places -> {OUT} ({OUT.stat().st_size // 1024} KiB)")


if __name__ == "__main__":
    main()
