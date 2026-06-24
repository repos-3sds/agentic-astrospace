import pytest
from unittest.mock import patch, MagicMock
from astrospace.core.chart import BirthChart
from astrospace.core.planets import PLANET_MEANINGS, SIGN_MEANINGS, HOUSE_MEANINGS, ASPECT_MEANINGS


def test_planet_meanings_complete():
    expected = ["Sun", "Moon", "Mercury", "Venus", "Mars",
                "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"]
    assert all(p in PLANET_MEANINGS for p in expected)


def test_sign_meanings_complete():
    signs = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
             "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
    assert all(s in SIGN_MEANINGS for s in signs)


def test_house_meanings_complete():
    assert all(i in HOUSE_MEANINGS for i in range(1, 13))


def test_aspect_meanings_keys():
    aspects = ["conjunction", "sextile", "square", "trine", "opposition", "quincunx"]
    assert all(a in ASPECT_MEANINGS for a in aspects)


def test_sign_has_required_fields():
    for sign, data in SIGN_MEANINGS.items():
        assert "element" in data, f"{sign} missing element"
        assert "modality" in data, f"{sign} missing modality"
        assert "keywords" in data, f"{sign} missing keywords"
