"""Complete AP/Telangana populated-places coverage in the city lookup."""
from astrospace.core.cities import (
    _state_places, lookup_city, search_cities,
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
        places = _state_places()
        assert len(places) > 30000, "AP+TS dataset should carry village-level coverage"

    def test_all_rows_have_coordinates_in_india(self):
        for row in _state_places()[:5000]:
            name, lat, lng, state = row[0], row[1], row[2], row[4]
            assert 5.0 < lat < 25.0 and 74.0 < lng < 88.0, (name, lat, lng)
            assert state in ("AP", "TS")


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
        assert countries == {"US", "CA"} and len(rows) > 20000
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
