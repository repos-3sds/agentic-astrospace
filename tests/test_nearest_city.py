"""'Use my location': an approximate position becomes the nearest known city."""
from fastapi.testclient import TestClient

from astrospace.core.cities import lookup_city, nearest_city
from main import app


def test_city_centre_returns_that_city():
    row = nearest_city(17.0005, 81.8040)
    assert (row["city"], row["nation"], row["timezone"]) == ("Rajahmundry", "IN", "Asia/Kolkata")
    assert row["distance_km"] < 2


def test_abroad_uses_the_local_clock():
    assert nearest_city(30.27, -97.74)["timezone"] == "America/Chicago"
    assert nearest_city(51.5, -0.12)["timezone"] == "Europe/London"


def test_every_answer_resolves_back_by_name():
    # The timing routes look places up by name; the row must lead back to
    # the same spot, not a bigger namesake elsewhere.
    for lat, lng in [(16.98, 82.10), (17.4, 78.5), (12.97, 77.59), (40.7, -74.0), (-33.87, 151.2)]:
        row = nearest_city(lat, lng)
        geo = lookup_city(row["city"], row["nation"])
        assert geo and abs(geo[0] - row["lat"]) < 0.05 and abs(geo[1] - row["lng"]) < 0.05


def test_far_from_anywhere_says_how_far():
    assert nearest_city(0, -30)["distance_km"] > 1000


def test_endpoint_takes_a_body_not_query_params():
    client = TestClient(app)
    r = client.post("/api/v1/panchanga/cities/nearest", json={"lat": 12.97, "lng": 77.59})
    assert r.status_code == 200
    assert r.json()["nation"] == "IN"
    assert client.post("/api/v1/panchanga/cities/nearest", json={"lat": 91, "lng": 0}).status_code == 422
    assert client.get("/api/v1/panchanga/cities/nearest", params={"lat": 12.97, "lng": 77.59}).status_code != 200
