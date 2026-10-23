"""Complete AP/Telangana populated-places coverage in the city lookup."""
from astrospace.core.cities import (
    _india_places, _normalize, lookup_city, search_cities,
)

# A spread of towns and smaller places across both states that must resolve.
AP_TS_PLACES = [
    "Bhimavaram", "Tenali", "Ongole", "Machilipatnam", "Srikakulam",
    "Anantapur", "Chittoor", "Proddatur", "Narasaraopet", "Tadepalligudem",
    "Karimnagar", "Nizamabad", "Khammam", "Mahbubnagar", "Siddipet",
    "Mancherial", "Suryapet", "Jagtial", "Sangareddy", "Kamareddy",
]


class TestDataset:
    def test_dataset_loads_and_is_complete_scale(self):
        places = _india_places()
        assert len(places) > 30000, "AP+TS dataset should carry village-level coverage"

    def test_all_rows_have_coordinates_in_india(self):
        places = _india_places()
        for row in range(5000):
            name, lat, lng = places.name(row), places.lat[row], places.lng[row]
            assert 5.0 < lat < 25.0 and 74.0 < lng < 88.0, (name, lat, lng)
            assert places.where(row)[1] in ("Andhra Pradesh", "Telangana")


class TestLookup:
    def test_known_towns_resolve(self):
        for place in AP_TS_PLACES:
            geo = lookup_city(place, "IN")
            assert geo is not None, f"{place} must resolve offline"
            lat, lng, tz = geo
            assert tz == "Asia/Kolkata"

    def test_village_level_lookup(self):
        # Small places that only exist in the GeoNames layer.
        for village in ("Pithapuram", "Samalkot", "Bhainsa", "Metpalli"):
            assert lookup_city(village, "IN") is not None, village

    def test_curated_entries_still_win(self):
        lat, lng, tz = lookup_city("Hyderabad", "IN")
        assert abs(lat - 17.385) < 0.01  # curated coordinates, not a GeoNames dup

    def test_non_indian_nation_does_not_hit_state_dataset(self):
        assert lookup_city("Siddipet", "US") is None


class TestSearch:
    def test_search_surfaces_state_places_with_district_labels(self):
        rows = search_cities("siddipet", limit=10)
        assert rows, "Siddipet should be searchable"
        assert any("Telangana" in row["label"] or row["nation"] == "IN" for row in rows)

    def test_search_prefix_ranks_bigger_towns_first(self):
        rows = search_cities("kari", limit=10)
        names = [row["city"].lower() for row in rows]
        assert any(name.startswith("karimnagar") for name in names)

    def test_curated_results_rank_before_state_layer(self):
        rows = search_cities("hyder", limit=5)
        assert rows[0]["city"].lower() == "hyderabad"

    def test_search_returns_bounded_results(self):
        assert len(search_cities("pal", limit=25)) <= 25


def test_a_city_its_timezone_is_named_after_leads_its_namesakes():
    labels = [row["label"] for row in search_cities("london", 5)]
    assert labels[0].startswith("London, GB")


class TestUSCanada:
    """GeoNames cities500 layer for the US and Canada (scripts/build_world_places.py)."""

    def test_dataset_covers_both_countries_with_their_own_timezones(self):
        from astrospace.core.cities import _world_places
        rows = _world_places()
        countries = {row[4] for row in rows}
        assert {"US", "CA"} <= countries and len(rows) > 100000
        zones = {row[6] for row in rows}
        assert {"America/St_Johns", "Pacific/Honolulu", "America/Regina",
                "America/Phoenix", "America/Anchorage"} <= zones

    def test_towns_beyond_the_curated_table_resolve(self):
        assert lookup_city("Fargo", "US")[2] == "America/Chicago"
        assert lookup_city("Saskatoon", "CA")[2] == "America/Regina"
        assert lookup_city("Montreal", "CA")[2] == "America/Toronto"  # diacritics folded

    def test_state_suffix_picks_the_namesake_that_was_chosen(self):
        il = lookup_city("Springfield, IL", "US")
        ma = lookup_city("Springfield, Massachusetts", "US")
        assert il[0] != ma[0]
        assert ma[2] == "America/New_York" and il[2] == "America/Chicago"
        assert lookup_city("Portland, ME", "US")[2] == "America/New_York"

    def test_curated_entries_still_win_and_nation_is_respected(self):
        assert lookup_city("Portland", "US")[2] == "America/Los_Angeles"
        # Vancouver, US must not fall through to the curated Vancouver, BC.
        assert abs(lookup_city("Vancouver", "US")[0] - 45.64) < 0.05
        assert lookup_city("Fargo", "IN") is None

    def test_search_returns_values_lookup_accepts(self):
        rows = search_cities("springfield", 8)
        assert len({row["city"] for row in rows}) == len(rows) > 3
        for row in rows:
            lat, lng, tz = lookup_city(row["city"], row["nation"])
            assert (lat, lng, tz) == (row["lat"], row["lng"], row["timezone"])

    def test_curated_city_hides_its_geonames_duplicate(self):
        cities = [row["city"] for row in search_cities("new york", 8)]
        assert "New York" in cities and "New York City, NY" not in cities

    def test_india_still_leads_short_prefixes(self):
        rows = search_cities("kari", 5)
        assert rows[0]["nation"] == "IN"


class TestIndiaAndDiaspora:
    """The same layer for the rest of India, the UK, the Gulf, Singapore,
    Malaysia, Australia, New Zealand and Europe."""

    def test_rest_of_india_resolves_with_state_names(self):
        assert lookup_city("Nanded", "IN") is not None
        maharashtra = lookup_city("Aurangabad", "IN")
        bihar = lookup_city("Aurangabad, Bihar", "IN")
        assert 24 < bihar[0] < 25.5 and 19 < maharashtra[0] < 20.5

    def test_ap_ts_villages_keep_answering_their_bare_names(self):
        # The village layer still wins over the all-India layer.
        assert lookup_city("Pithapuram", "IN") is not None
        from astrospace.core.cities import _world_places
        regions = {row[3] for row in _world_places() if row[4] == "IN"}
        assert "Andhra Pradesh" not in regions and "Telangana" not in regions

    def test_diaspora_cities_carry_their_own_zones(self):
        assert lookup_city("Leicester", "GB")[2] == "Europe/London"
        assert lookup_city("Sharjah", "AE")[2] == "Asia/Dubai"
        assert lookup_city("Klang", "MY")[2] == "Asia/Kuala_Lumpur"
        assert lookup_city("Frankfurt am Main", "DE")[2] == "Europe/Berlin"
        assert lookup_city("Auckland", "NZ")[2] == "Pacific/Auckland"

    def test_same_name_in_two_countries_stays_apart(self):
        assert lookup_city("Perth", "AU")[2] == "Australia/Perth"
        assert lookup_city("Perth, Scotland", "GB")[2] == "Europe/London"

    def test_every_world_result_round_trips_through_lookup(self):
        for query in ("perth", "leic", "aurang", "kuala", "sharj", "frank", "dub"):
            for row in search_cities(query, 8):
                geo = lookup_city(row["city"], row["nation"])
                assert geo is not None, row
                assert (geo[0], geo[1]) == (row["lat"], row["lng"]), row

    def test_big_foreign_cities_beat_villages_but_not_indian_towns(self):
        cities = [row["city"] for row in search_cities("dub", 8)]
        assert cities.count("Dubai") == 1 and any(c.startswith("Dublin") for c in cities)
        names = [row["city"] for row in search_cities("dubb", 5)]
        assert all(row["nation"] == "IN" for row in search_cities("dubb", 5)), names


class TestAllIndiaLayer:
    """The village layer as it grows to all of India (scripts/build_india_places.py):
    places save as "Name, District" so namesakes stay apart, and bare AP/TS
    names saved before keep resolving where they did."""

    def test_search_results_round_trip_to_the_village_picked(self):
        for query in ("guntur", "kari", "rampur", "aurang"):
            for row in search_cities(query, 30):
                geo = lookup_city(row["city"], row["nation"])
                assert geo is not None, row
                assert (geo[0], geo[1]) == (row["lat"], row["lng"]), row

    def test_a_namesake_far_from_the_curated_city_is_offered_with_its_district(self):
        cities = [row["city"] for row in search_cities("guntur", 30)]
        assert "Guntur" in cities
        assert any(city.startswith("Guntur, ") for city in cities)

    def test_bare_names_saved_before_still_resolve(self):
        assert lookup_city("Bhainsa", "IN") is not None
        assert lookup_city("Pithapuram", "") is not None

    def test_qualifier_must_match(self):
        assert lookup_city("Bhainsa, Nirmal", "IN") is not None
        assert lookup_city("Bhainsa, Kerala", "IN") is None or \
            lookup_city("Bhainsa, Kerala", "IN") != lookup_city("Bhainsa, Nirmal", "IN")


def _write_dump(tmp_path):
    def place(gid, name, lat, lng, admin1, admin2, pop, alts=""):
        cols = [str(gid), name, name, alts, str(lat), str(lng), "P", "PPL", "IN", "",
                admin1, admin2, "", "", str(pop), "", "", "Asia/Kolkata", "2024-01-01"]
        return "\t".join(cols)
    (tmp_path / "IN.txt").write_text("\n".join([
        place(1, "Rampur", 28.8, 79.0, "36", "001", 300000),
        place(2, "Rampur", 25.6, 85.1, "34", "002", 10),
        place(3, "Rāmpur", 25.7, 85.2, "34", "002", 0),  # same district, folded: one kept
        place(4, "Aurangabad", 24.75, 84.37, "34", "003", 100000),
        place(5, "Aurangabad", 19.88, 75.34, "16", "004", 1200000, "Sambhajinagar"),
        place(6, "Bhainsa", 19.1, 77.96, "40", "005", 50000),
        place(7, "Hill, Top", 30.0, 78.0, "39", "", 0),
    ]) + "\n", encoding="utf-8")
    (tmp_path / "admin1.txt").write_text("\n".join([
        "IN.36\tUttar Pradesh\tUttar Pradesh\t1", "IN.34\tBihar\tBihar\t2",
        "IN.16\tMaharashtra\tMaharashtra\t3", "IN.40\tTelangana\tTelangana\t4",
        "IN.39\tUttarakhand\tUttarakhand\t5",
    ]), encoding="utf-8")
    (tmp_path / "admin2.txt").write_text("\n".join([
        "IN.36.001\tRampur\tRampur\t1", "IN.34.002\tPatna\tPatna\t2",
        "IN.34.003\tAurangabad\tAurangabad\t3", "IN.16.004\tAurangabad\tAurangabad\t4",
        "IN.40.005\tNirmal\tNirmal\t5",
    ]), encoding="utf-8")


class TestIndiaBuilder:
    """build_india_places.py output, read back by the compact loader."""

    def _places(self, tmp_path, monkeypatch, extra: str = ""):
        import importlib.util
        import sys
        from pathlib import Path
        from astrospace.core import cities
        _write_dump(tmp_path)
        if extra:
            with (tmp_path / "IN.txt").open("a") as fh:
                fh.write(extra + "\n")
        script = Path(__file__).resolve().parent.parent / "scripts" / "build_india_places.py"
        sys.path.insert(0, str(script.parent))
        spec = importlib.util.spec_from_file_location("build_india_places", script)
        builder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(builder)
        out = tmp_path / "india_places.tsv.gz"
        monkeypatch.setattr(builder, "OUT", out)
        monkeypatch.setattr(sys, "argv", ["x", str(tmp_path / "IN.txt"),
                                          str(tmp_path / "admin1.txt"), str(tmp_path / "admin2.txt")])
        builder.main()
        return cities._IndiaPlaces(out)

    def test_rows_and_saved_names(self, tmp_path, monkeypatch):
        places = self._places(tmp_path, monkeypatch)
        assert len(places) == 6  # the second Patna Rampur folds into the first
        by_city = {places.city(row): row for row in range(len(places))}
        # District named after the town: the state says more.
        assert "Rampur, Uttar Pradesh" in by_city
        assert "Rampur, Patna" in by_city
        assert "Aurangabad, Maharashtra" in by_city and "Aurangabad, Bihar" in by_city
        assert "Bhainsa, Nirmal" in by_city
        assert "Hill Top, Uttarakhand" in by_city  # commas would split the saved name

    def test_lookup_forms(self, tmp_path, monkeypatch):
        places = self._places(tmp_path, monkeypatch)
        for row in range(len(places)):
            assert places.lookup(_normalize(places.city(row))) == row
        bihar = places.lookup("aurangabad, bihar")
        assert places.where(bihar)[1] == "Bihar"
        assert places.lookup("aurangabad") == places.lookup("aurangabad, maharashtra")
        assert places.lookup("sambhajinagar") == places.lookup("aurangabad, maharashtra")
        assert places.lookup("rampur, kerala") is None
        # Bare names lean to AP/Telangana, where they were saved before.
        assert places.where(places.lookup("bhainsa"))[1] == "Telangana"

    def test_search_buckets(self, tmp_path, monkeypatch):
        places = self._places(tmp_path, monkeypatch)
        exact, prefix, contains = places.search("rampur", 10)
        assert len(exact) == 2 and not prefix and not contains
        assert places.search("ramp", 10)[1] == exact
        assert [places.name(r) for r in places.search("ampu", 10)[2]] == ["Rampur", "Rampur"]

    def test_unknown_state_code_stops_the_build(self, tmp_path, monkeypatch):
        import pytest
        newtown = "\t".join(["9", "Newtown", "Newtown", "", "20", "80", "P", "PPL", "IN", "",
                             "99", "", "", "", "0", "", "", "Asia/Kolkata", "x"])
        with pytest.raises(SystemExit, match="99"):
            self._places(tmp_path, monkeypatch, extra=newtown)
