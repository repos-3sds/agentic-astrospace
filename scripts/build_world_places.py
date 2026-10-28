"""
Build the country-level populated-places dataset for the city search/lookup in
astrospace/core/cities.py: the US and Canada, the UK and Ireland, the Gulf, Singapore, Malaysia, Australia, New Zealand and
Europe.

Usage:
    python scripts/build_world_places.py cities500.(txt|json) rg_cities1000.csv

Data sources, all GeoNames (geonames.org), licensed CC-BY 4.0:
- cities500: every populated place with 500+ people, either the raw dump
  https://download.geonames.org/export/dump/cities500.zip or the same data as
  JSON in the `geonamescache` PyPI package (geonamescache/data/cities500.json).
- region names: GeoNames admin1 codes are opaque ("16" is Maharashtra), so
  names come from admin1CodesASCII.txt as joined onto places in the
  `reverse_geocoder` PyPI package (reverse_geocoder/rg_cities1000.csv),
  matched by country and coordinates. That copy predates some renames
  (France's 2016 regions, Delhi as "NCT"), which _REGION_OVERRIDES corrects.

Output: astrospace/core/data/world_places.json.gz — a JSON list of
[name, lat, lng, region, country, population, timezone]. `region` is what the
app shows after the name: the state code for the US and Canada (TX, ON), the
region name elsewhere (Maharashtra, England), or "" where a country's first
level is too fine to help (Malta's 68 councils) or absent (Singapore).
Rows run in search order: population, with Indian places weighted up.
GeoNames carries the IANA timezone per place.
"""
from __future__ import annotations

import csv
import gzip
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

EUROPE = ["AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE", "GR",
          "HU", "IT", "LV", "LT", "LU", "MT", "NL", "PL", "PT", "RO", "SK", "SI",
          "ES", "SE", "CH", "NO", "IS"]
# India comes from the village-level layer (build_india_places.py), so a
# town is not listed twice.
COUNTRIES = ["US", "CA", "GB", "IE", "AE", "SA", "QA", "KW", "OM", "BH",
             "SG", "MY", "AU", "NZ", *EUROPE]

# Countries shown without a region: city-states, or first levels so fine they
# name the town itself.
NO_REGION = {"SG", "BH", "KW", "QA", "MT", "SI", "LV", "LU", "IS"}

# GeoNames admin1 codes for Canada are numeric; show the postal abbreviations.
_CA_PROVINCES = {
    "01": "AB", "02": "BC", "03": "MB", "04": "NB", "05": "NL", "07": "NS",
    "08": "ON", "09": "PE", "10": "QC", "11": "SK", "12": "YT", "13": "NT",
    "14": "NU",
}

_REGION_OVERRIDES: dict[str, dict[str, str]] = {
    "IN": {"01": "Andaman and Nicobar Islands", "02": "Andhra Pradesh", "40": "Telangana", "07": "Delhi", "12": "Jammu and Kashmir", "41": "Ladakh",
           "14": "Lakshadweep", "22": "Puducherry",
           "52": "Dadra and Nagar Haveli and Daman and Diu"},
    "AE": {"01": "Abu Dhabi", "02": "Ajman", "03": "Dubai", "04": "Fujairah",
           "05": "Ras Al Khaimah", "06": "Sharjah", "07": "Umm Al Quwain"},
    "SA": {"02": "Al Bahah", "05": "Madinah", "06": "Eastern Province",
           "08": "Al Qassim", "10": "Riyadh", "11": "Asir", "13": "Hail",
           "14": "Makkah", "15": "Northern Borders", "16": "Najran",
           "17": "Jazan", "19": "Tabuk", "20": "Al Jawf"},
    "OM": {"01": "Ad Dakhiliyah", "02": "Al Batinah South", "03": "Al Wusta",
           "04": "Ash Sharqiyah South", "06": "Muscat", "07": "Musandam",
           "08": "Dhofar", "09": "Ad Dhahirah", "10": "Al Buraimi",
           "11": "Al Batinah North", "12": "Ash Sharqiyah North"},
    "FR": {"11": "Île-de-France", "24": "Centre-Val de Loire",
           "27": "Bourgogne-Franche-Comté", "28": "Normandy",
           "32": "Hauts-de-France", "44": "Grand Est", "52": "Pays de la Loire",
           "53": "Brittany", "75": "Nouvelle-Aquitaine", "76": "Occitanie",
           "84": "Auvergne-Rhône-Alpes", "93": "Provence-Alpes-Côte d'Azur",
           "94": "Corsica"},
    "DE": {"01": "Baden-Württemberg", "03": "Bremen", "08": "Rhineland-Palatinate"},
    "BG": {"40": "Dobrich", "45": "Kyustendil"},
    "CZ": {"85": "Moravian-Silesian"},
    "LT": {"59": "Marijampolė"},
    "SK": {"06": "Trenčín"},
}

OUT = Path(__file__).resolve().parent.parent / "astrospace" / "core" / "data" / "world_places.json.gz"


def _records(path: Path):
    """Yield (name, lat, lng, country, admin1, population, timezone)."""
    if path.suffix == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        for rec in (data.values() if isinstance(data, dict) else data):
            yield (rec["name"], float(rec["latitude"]), float(rec["longitude"]),
                   rec["countrycode"], rec.get("admin1code") or "",
                   int(rec.get("population") or 0), rec.get("timezone") or "")
        return
    for line in path.open(encoding="utf-8"):
        parts = line.rstrip("\n").split("\t")
        if len(parts) < 18 or parts[6] != "P":
            continue
        yield (parts[1], float(parts[4]), float(parts[5]), parts[8], parts[10],
               int(parts[14] or 0), parts[17])


def region_names(records: list[tuple], rg_csv: Path) -> dict[tuple[str, str], str]:
    """(country, admin1 code) -> region name, by majority vote of the places
    the reverse_geocoder table names at the same coordinates."""
    named: dict[tuple, str] = {}
    with rg_csv.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            named[(row["cc"], round(float(row["lat"]), 3), round(float(row["lon"]), 3))] = row["admin1"]
    votes: dict[tuple[str, str], Counter] = defaultdict(Counter)
    for _, lat, lng, country, admin1, _, _ in records:
        name = named.get((country, round(lat, 3), round(lng, 3)))
        if name:
            votes[(country, admin1)][name] += 1
    names = {key: counter.most_common(1)[0][0] for key, counter in votes.items()}
    for country, overrides in _REGION_OVERRIDES.items():
        for code, name in overrides.items():
            names[(country, code)] = name
    return names


def search_weight(population: int, country: str) -> int:
    """Search order: population, with Indian places counted 20x and never
    below 2,500 (GeoNames leaves most villages at 0). Keep in step with
    astrospace/core/cities.py `_search_weight`."""
    return max(population, 2500) * 20 if country == "IN" else population


def region_for(country: str, admin1: str, names: dict) -> str:
    if country == "US":
        return admin1
    if country == "CA":
        return _CA_PROVINCES.get(admin1, "")
    if country in NO_REGION:
        return ""
    return names.get((country, admin1), "")


def build(source: Path, rg_csv: Path) -> list[list]:
    wanted = set(COUNTRIES)
    records = [rec for rec in _records(source) if rec[3] in wanted and rec[6]]
    names = region_names(records, rg_csv)
    best: dict[tuple[str, str, str], list] = {}
    for name, lat, lng, country, admin1, population, tz in records:
        name = name.strip()
        region = region_for(country, admin1, names)
        if not name or (country in ("US", "CA") and not region):
            continue
        row = [name, round(lat, 4), round(lng, 4), region, country, population, tz]
        # Same name in the same region: keep the more populous record.
        key = (name.lower(), region.lower(), country)
        if key not in best or population > best[key][5]:
            best[key] = row
    return sorted(best.values(), key=lambda r: (-search_weight(r[5], r[4]), r[0]))


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    rows = build(Path(sys.argv[1]), Path(sys.argv[2]))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "source": "GeoNames (geonames.org) cities500 and admin1 codes, CC-BY 4.0",
        "countries": COUNTRIES,
        "count": len(rows),
        "places": rows,
    }
    with gzip.open(OUT, "wt", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, separators=(",", ":"))
    by_country = Counter(row[4] for row in rows)
    print(f"wrote {len(rows)} places -> {OUT} ({OUT.stat().st_size // 1024} KiB)")
    print(", ".join(f"{cc} {n}" for cc, n in by_country.most_common()))


if __name__ == "__main__":
    main()
