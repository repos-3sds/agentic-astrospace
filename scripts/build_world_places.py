"""
Build the country-level populated-places dataset (currently the US and Canada)
for the city search/lookup in astrospace/core/cities.py.

Usage:
    python scripts/build_world_places.py /path/to/cities500.(txt|json)

Data source: GeoNames cities500 (every populated place with 500+ people), either
the raw dump https://download.geonames.org/export/dump/cities500.zip or the
same data as JSON in the `geonamescache` PyPI package
(geonamescache/data/cities500.json). GeoNames is licensed CC-BY 4.0 —
attribution: GeoNames (geonames.org).

Output: astrospace/core/data/world_places.json.gz — a JSON list of
[name, lat, lng, region, country, population, timezone], population-sorted so
search ranks bigger places first. `region` is the state/province code (TX, ON);
GeoNames carries the IANA timezone per place, which matters here because the
US and Canada span six zones and several counties differ from their state.

Extend COUNTRIES to cover more of the world; values map GeoNames admin1 codes
to the short region codes shown in the app (None keeps the GeoNames code).
"""
from __future__ import annotations

import gzip
import json
import sys
from pathlib import Path

# GeoNames admin1 codes for Canada are numeric; show the postal abbreviations.
_CA_PROVINCES = {
    "01": "AB", "02": "BC", "03": "MB", "04": "NB", "05": "NL", "07": "NS",
    "08": "ON", "09": "PE", "10": "QC", "11": "SK", "12": "YT", "13": "NT",
    "14": "NU",
}

COUNTRIES: dict[str, dict[str, str] | None] = {
    "US": None,  # admin1 is already the two-letter state code
    "CA": _CA_PROVINCES,
}

OUT = Path(__file__).resolve().parent.parent / "astrospace" / "core" / "data" / "world_places.json.gz"


def _records(path: Path):
    """Yield (name, lat, lng, country, admin1, population, timezone)."""
    if path.suffix == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        for rec in (data.values() if isinstance(data, dict) else data):
            yield (rec["name"], rec["latitude"], rec["longitude"], rec["countrycode"],
                   rec.get("admin1code") or "", int(rec.get("population") or 0),
                   rec.get("timezone") or "")
        return
    for line in path.open(encoding="utf-8"):
        parts = line.rstrip("\n").split("\t")
        if len(parts) < 18 or parts[6] != "P":
            continue
        yield (parts[1], float(parts[4]), float(parts[5]), parts[8], parts[10],
               int(parts[14] or 0), parts[17])


def build(source: Path) -> list[list]:
    best: dict[tuple[str, str, str], list] = {}
    for name, lat, lng, country, admin1, population, tz in _records(source):
        if country not in COUNTRIES or not tz:
            continue
        name = name.strip()
        codes = COUNTRIES[country]
        region = codes.get(admin1, "") if codes is not None else admin1
        if not name or not region:
            continue
        row = [name, round(float(lat), 4), round(float(lng), 4), region, country,
               population, tz]
        # Same name in the same state: keep the more populous record.
        key = (name.lower(), region, country)
        if key not in best or population > best[key][5]:
            best[key] = row
    return sorted(best.values(), key=lambda r: (-r[5], r[0]))


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    rows = build(Path(sys.argv[1]))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "source": "GeoNames (geonames.org) cities500, CC-BY 4.0",
        "countries": sorted(COUNTRIES),
        "count": len(rows),
        "places": rows,
    }
    with gzip.open(OUT, "wt", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, separators=(",", ":"))
    print(f"wrote {len(rows)} places -> {OUT} ({OUT.stat().st_size // 1024} KiB)")


if __name__ == "__main__":
    main()
