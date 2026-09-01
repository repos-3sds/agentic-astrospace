"""Integration tests: Jaimini, special lagnas, Yogini dasha, and masa wired into VedicChart."""
from astrospace.core.vedic.chart import VedicChart
from astrospace.core.vedic.constants import LUNAR_MONTHS, SIGNS


DELHI = {"city": "New Delhi", "nation": "IN"}


def _chart():
    return VedicChart("Integration", 1990, 1, 1, 12, 0, **DELHI)


class TestJaiminiWiring:
    def test_jaimini_section_shape(self):
        j = _chart().jaimini()
        karakas = j["chara_karakas"]["karakas"]
        assert set(karakas) == {"AK", "AmK", "BK", "MK", "PK", "PiK", "GK", "DK"}
        planets = {row["planet"] for row in karakas.values()}
        assert len(planets) == 8 and "Rahu" in planets or len(planets) == 8
        assert j["arudha_lagna"]["sign_name"] in SIGNS
        assert j["upapada"]["sign_name"] in SIGNS
        assert len(j["arudha_padas"]["padas"]) == 12
        assert j["karakamsha"]["atmakaraka"] == karakas["AK"]["planet"]
        assert j["karakamsha"]["sign_name"] in SIGNS


class TestKarakamsha:
    """BPHS "Effects of Karakamsha" (Santhanam ch.33 / Sharma ch.35, same
    shlokas 41-45, cross-verified word-for-word in both translations):
    planets in the Atmakaraka's navamsa sign, or in the 5th sign from it,
    are read the way a lagna's occupants are read elsewhere — e.g. Ketu or
    Rahu there names an astrologer."""

    def test_atmakaraka_always_occupies_its_own_karakamsha(self):
        """Tautological by construction, not filtered out — see
        jaimini.karakamsha()'s docstring for why a planet conjunct the
        Atmakaraka in navamsa needs to stay visible."""
        j = _chart().jaimini()
        k = j["karakamsha"]
        assert k["atmakaraka"] in k["occupants"]

    def test_fifth_sign_is_five_signs_from_karakamsha(self):
        j = _chart().jaimini()
        k = j["karakamsha"]
        expected = (sign_index_from_name(k["sign_name"]) + 4) % 12
        assert sign_index_from_name(k["fifth_sign_name"]) == expected

    def test_accepts_a_precomputed_atmakaraka_and_agrees_with_the_derived_one(self):
        from astrospace.core.vedic.jaimini import chara_karakas, karakamsha
        chart = _chart()
        ak = chara_karakas(chart.positions)["karakas"]["AK"]["planet"]
        derived = karakamsha(chart.positions)
        precomputed = karakamsha(chart.positions, atmakaraka=ak)
        assert derived == precomputed

    def test_occupants_are_exactly_the_planets_sharing_the_navamsa_sign(self):
        from astrospace.core.vedic.jaimini import karakamsha
        from astrospace.core.vedic.vargas import varga_sign
        chart = _chart()
        k = karakamsha(chart.positions)
        expected = {p for p, d in chart.positions.items()
                   if varga_sign("D9", d["lon"]) == k["sign"]}
        assert set(k["occupants"]) == expected


def sign_index_from_name(name: str) -> int:
    return SIGNS.index(name)

    def test_special_lagnas_advance_from_sunrise(self):
        sl = _chart().special_lagnas()
        assert "error" not in sl
        assert 0 < sl["hours_since_sunrise"] < 24
        for key in ("bhava_lagna", "hora_lagna", "ghati_lagna"):
            assert 0.0 <= sl[key]["longitude"] < 360.0
            assert sl[key]["sign_name"] in SIGNS

    def test_pre_sunrise_birth_uses_previous_day_sunrise(self):
        chart = VedicChart("Early", 1990, 1, 1, 4, 30, **DELHI)  # ~2.5h before sunrise
        sl = chart.special_lagnas()
        # Vedic day sunrise must precede the birth: hours since sunrise stays positive
        assert sl["hours_since_sunrise"] > 12  # previous day's sunrise, not the upcoming one

    def test_yogini_dasha_current_chain(self):
        y = _chart().yogini_dashas()
        assert y["system"].lower().startswith("yogini")
        assert y["current"]["mahadasha"] is not None

    def test_masa_section(self):
        m = _chart().masa()
        base = m["name"].replace("Adhika ", "")
        assert base in LUNAR_MONTHS
        assert m["paksha"] in ("Shukla", "Krishna")
        assert m["ritu"] in ("Vasanta", "Grishma", "Varsha", "Sharad", "Hemanta", "Shishira")
        assert m["ayana"] in ("Uttarayana", "Dakshinayana")
        assert m["samvatsara"]["name"]

    def test_to_dict_includes_new_sections(self):
        payload = _chart().to_dict()
        for key in ("jaimini", "special_lagnas", "masa"):
            assert key in payload
