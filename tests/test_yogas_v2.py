"""Tests for the second wave of deterministic yogas (Chandra/Surya/Adhi/Amala/
Saraswati/Kartari/Shakata/Guru-Chandala) plus sambandha grading and
dignity-aware strength adjustments."""
import pytest

from astrospace.core.vedic.yogas import yoga_summary

PLANET_ORDER = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]


def chart(sun, moon, mars, mercury, jupiter, venus, saturn, rahu, ketu):
    lons = [sun, moon, mars, mercury, jupiter, venus, saturn, rahu, ketu]
    return {name: {"lon": float(lon)} for name, lon in zip(PLANET_ORDER, lons)}


def rows(result, rule_id):
    return [r for r in result["all"] if r["rule_id"] == rule_id]


def one(result, rule_id):
    matches = rows(result, rule_id)
    assert len(matches) == 1, f"expected exactly one {rule_id} row, got {len(matches)}"
    return matches[0]


def notes_text(row):
    return " ".join(row["notes"])


class TestChandraYogas:
    def test_sunapha_active_and_kemadruma_inactive(self):
        # Moon Taurus; Mars in Gemini (2nd from Moon); Aries (12th) holds only Sun.
        result = yoga_summary(chart(10, 40, 65, 130, 160, 190, 280, 100, 280), 0.0)
        sunapha = one(result, "sunapha_yoga")
        assert sunapha["active"] and sunapha["strength"] == "moderate"
        assert "Mars" in sunapha["planets"]
        # Sun in the 12th from Moon does not count for Anapha.
        assert not one(result, "anapha_yoga")["active"]
        assert not one(result, "durudhara_yoga")["active"]
        # Adjacent support (Mars) means Kemadruma cannot be active alongside Sunapha.
        assert not one(result, "kemadruma_yoga")["active"]

    def test_anapha_active_when_only_twelfth_occupied(self):
        # Moon Taurus; Venus in Aries (12th from Moon); Gemini empty.
        result = yoga_summary(chart(130, 40, 220, 160, 250, 10, 280, 100, 280), 0.0)
        anapha = one(result, "anapha_yoga")
        assert anapha["active"] and "Venus" in anapha["planets"]
        assert not one(result, "sunapha_yoga")["active"]
        assert not one(result, "durudhara_yoga")["active"]

    def test_durudhara_subsumes_sunapha_and_anapha(self):
        # Moon Taurus; Mars Gemini (2nd), Venus Aries (12th).
        result = yoga_summary(chart(130, 40, 65, 160, 250, 10, 280, 100, 280), 0.0)
        durudhara = one(result, "durudhara_yoga")
        assert durudhara["active"] and durudhara["strength"] == "strong"
        sunapha = one(result, "sunapha_yoga")
        anapha = one(result, "anapha_yoga")
        # Durudhara implies both flanking houses occupied: both still report active.
        assert sunapha["active"] and anapha["active"]
        assert "Subsumed by Durudhara" in notes_text(sunapha)
        assert "Subsumed by Durudhara" in notes_text(anapha)

    def test_chandra_yogas_negative_nodes_do_not_count(self):
        # Moon Taurus; Rahu in Aries (12th) is excluded; Gemini empty.
        result = yoga_summary(chart(130, 40, 220, 160, 250, 190, 280, 10, 190), 0.0)
        assert not one(result, "sunapha_yoga")["active"]
        assert not one(result, "anapha_yoga")["active"]
        assert not one(result, "durudhara_yoga")["active"]


class TestSuryaYogas:
    def test_vesi_active_moon_does_not_count(self):
        # Sun Aries; Jupiter Taurus (2nd from Sun); Pisces (12th) holds only Moon.
        result = yoga_summary(chart(10, 340, 220, 160, 40, 190, 280, 100, 280), 0.0)
        vesi = one(result, "vesi_yoga")
        assert vesi["active"] and "Jupiter" in vesi["planets"]
        assert not one(result, "vosi_yoga")["active"]
        assert not one(result, "ubhayachari_yoga")["active"]

    def test_ubhayachari_subsumes_vesi_and_vosi(self):
        # Sun Aries; Mars Taurus (2nd), Saturn Pisces (12th).
        result = yoga_summary(chart(10, 130, 40, 160, 250, 190, 340, 100, 280), 0.0)
        ubhaya = one(result, "ubhayachari_yoga")
        assert ubhaya["active"] and ubhaya["strength"] == "strong"
        vesi = one(result, "vesi_yoga")
        vosi = one(result, "vosi_yoga")
        assert vesi["active"] and vosi["active"]
        assert "Subsumed by Ubhayachari" in notes_text(vesi)
        assert "Subsumed by Ubhayachari" in notes_text(vosi)

    def test_surya_yogas_negative(self):
        # Sun Aries; Taurus holds only Moon, Pisces only Rahu — both excluded.
        result = yoga_summary(chart(10, 40, 220, 160, 250, 190, 100, 340, 160), 0.0)
        assert not one(result, "vesi_yoga")["active"]
        assert not one(result, "vosi_yoga")["active"]
        assert not one(result, "ubhayachari_yoga")["active"]


class TestAdhiYoga:
    def test_all_three_houses_is_strong(self):
        # Moon Aries; Mercury Virgo (6th), Venus Libra (7th), Jupiter Scorpio (8th).
        result = yoga_summary(chart(35, 5, 275, 155, 215, 185, 305, 65, 245), 0.0)
        adhi = one(result, "adhi_yoga")
        assert adhi["active"] and adhi["strength"] == "strong"

    def test_two_of_three_houses_is_moderate(self):
        # Mercury Virgo (6th), Venus Libra (7th), Jupiter away in Cancer.
        result = yoga_summary(chart(35, 5, 275, 155, 100, 185, 305, 65, 245), 0.0)
        adhi = one(result, "adhi_yoga")
        assert adhi["active"] and adhi["strength"] == "moderate"

    def test_single_house_is_inactive(self):
        # Only Mercury in Virgo (6th from Moon).
        result = yoga_summary(chart(35, 5, 275, 155, 100, 65, 305, 125, 305), 0.0)
        assert not one(result, "adhi_yoga")["active"]


class TestAmalaYoga:
    def test_benefic_in_tenth_from_lagna(self):
        # Aries lagna; Venus in Capricorn (10th from Lagna); Moon Leo, its 10th (Taurus) empty.
        result = yoga_summary(chart(130, 125, 220, 160, 250, 280, 340, 100, 280), 0.0)
        amala = one(result, "amala_yoga")
        assert amala["active"] and "Venus" in amala["planets"]
        assert "Anchor(s): Lagna." in amala["notes"]

    def test_benefic_in_tenth_from_moon(self):
        # Moon Leo; Jupiter in Taurus (10th from Moon); Capricorn (10th from Lagna) has no benefic.
        result = yoga_summary(chart(130, 125, 220, 160, 40, 190, 280, 100, 280), 0.0)
        amala = one(result, "amala_yoga")
        assert amala["active"] and "Jupiter" in amala["planets"]
        assert "Anchor(s): Moon." in amala["notes"]

    def test_inactive_without_benefic_in_either_tenth(self):
        # Saturn (malefic) in Capricorn does not create Amala.
        result = yoga_summary(chart(130, 125, 220, 160, 250, 190, 280, 100, 280), 0.0)
        assert not one(result, "amala_yoga")["active"]


class TestSaraswatiYoga:
    def test_active_with_jupiter_own_sign(self):
        # Aries lagna; Jupiter Sagittarius (9th, own), Venus Libra (7th), Mercury Aries (1st).
        result = yoga_summary(chart(35, 100, 305, 5, 245, 185, 280, 155, 335), 0.0)
        saraswati = one(result, "saraswati_yoga")
        assert saraswati["active"] and saraswati["strength"] == "strong"

    def test_inactive_when_jupiter_lacks_dignity(self):
        # Jupiter in Capricorn: 10th house is fine but Saturn is not a natural friend of Jupiter.
        result = yoga_summary(chart(35, 100, 305, 5, 275, 185, 130, 155, 335), 0.0)
        assert not one(result, "saraswati_yoga")["active"]

    def test_inactive_when_benefic_outside_allowed_houses(self):
        # Mercury in Gemini = 3rd house from Aries lagna.
        result = yoga_summary(chart(35, 100, 305, 65, 245, 185, 280, 155, 335), 0.0)
        assert not one(result, "saraswati_yoga")["active"]


class TestKartariYogas:
    def test_shubha_kartari_from_lagna(self):
        # Aries lagna; Venus Pisces (12th) and Jupiter Taurus (2nd), no malefics there.
        result = yoga_summary(chart(130, 125, 220, 160, 40, 340, 250, 100, 280), 0.0)
        shubha = rows(result, "shubha_kartari_yoga")
        assert len(shubha) == 2  # one entry per anchor
        by_anchor = {r["name"]: r for r in shubha}
        assert by_anchor["Shubha Kartari Yoga (from Lagna)"]["active"]
        assert not by_anchor["Shubha Kartari Yoga (from Moon)"]["active"]
        assert not any(r["active"] for r in rows(result, "papa_kartari_yoga"))

    def test_papa_kartari_from_moon(self):
        # Moon Leo; Mars Cancer (12th from Moon) and Saturn Virgo (2nd), no benefics there.
        result = yoga_summary(chart(130, 125, 100, 15, 250, 190, 155, 310, 130), 0.0)
        papa = {r["name"]: r for r in rows(result, "papa_kartari_yoga")}
        assert papa["Papa Kartari Yoga (from Moon)"]["active"]
        assert not papa["Papa Kartari Yoga (from Lagna)"]["active"]
        assert not any(r["active"] for r in rows(result, "shubha_kartari_yoga"))

    def test_mixed_occupancy_activates_neither(self):
        # Benefic and malefic mixed around Lagna: Venus Pisces, Mars Taurus.
        result = yoga_summary(chart(130, 125, 40, 160, 250, 340, 280, 100, 280), 0.0)
        assert not any(r["active"] for r in rows(result, "shubha_kartari_yoga") if "Lagna" in r["name"])
        assert not any(r["active"] for r in rows(result, "papa_kartari_yoga") if "Lagna" in r["name"])


class TestShakataYoga:
    def test_active_when_moon_sixth_from_jupiter(self):
        # Jupiter Aries, Moon Virgo (6th from Jupiter, 6th house from Aries lagna — no kendra).
        result = yoga_summary(chart(35, 155, 220, 65, 5, 190, 280, 100, 280), 0.0)
        shakata = one(result, "shakata_yoga")
        assert shakata["active"]
        assert any("6 from Jupiter" in t for t in shakata["triggers"])

    def test_cancelled_by_kendra_moon(self):
        # Same Moon/Jupiter, but Gemini lagna puts Moon in the 4th house (kendra).
        result = yoga_summary(chart(35, 155, 220, 65, 5, 190, 280, 100, 280), 60.0)
        shakata = one(result, "shakata_yoga")
        assert not shakata["active"]
        assert "Cancelled: Moon occupies a kendra from Lagna." in shakata["notes"]

    def test_inactive_when_moon_not_in_dusthana_from_jupiter(self):
        # Moon Leo = 5th from Jupiter in Aries.
        result = yoga_summary(chart(35, 130, 220, 65, 5, 190, 280, 100, 280), 0.0)
        shakata = one(result, "shakata_yoga")
        assert not shakata["active"]
        assert "Cancelled: Moon occupies a kendra from Lagna." not in shakata["notes"]


class TestGuruChandalaYoga:
    def test_jupiter_rahu_conjunction_is_primary(self):
        result = yoga_summary(chart(130, 250, 220, 160, 42, 190, 280, 47, 227), 0.0)
        gc = one(result, "guru_chandala_yoga")
        assert gc["active"] and gc["strength"] == "moderate"
        assert set(gc["planets"]) == {"Jupiter", "Rahu"}

    def test_jupiter_ketu_variant_is_milder(self):
        result = yoga_summary(chart(130, 250, 310, 160, 222, 190, 280, 47, 227), 0.0)
        gc = one(result, "guru_chandala_yoga")
        assert gc["active"] and gc["strength"] == "weak"
        assert set(gc["planets"]) == {"Jupiter", "Ketu"}
        assert "milder" in notes_text(gc)

    def test_inactive_when_jupiter_apart_from_nodes(self):
        result = yoga_summary(chart(10, 250, 310, 160, 130, 190, 280, 47, 227), 0.0)
        assert not one(result, "guru_chandala_yoga")["active"]


class TestSambandhaGrading:
    def test_one_way_graha_drishti_grades_weak(self):
        # Aries lagna. Saturn (10th lord) in Leo throws its 10th aspect onto
        # Sun (5th lord) in Taurus; Sun does not aspect back.
        result = yoga_summary(chart(40, 305, 10, 70, 190, 280, 125, 155, 335), 0.0)
        raja = [r for r in rows(result, "raja_yoga") if set(r["planets"]) == {"Saturn", "Sun"}]
        assert len(raja) == 1
        assert raja[0]["strength"] == "weak"
        assert any("one-way graha drishti (partial sambandha)" in t for t in raja[0]["triggers"])

    def test_parivartana_grades_moderate(self):
        # Taurus lagna. Sun (4th lord) in Gemini and Mercury (5th lord) in Leo
        # exchange signs; neither is debilitated, exalted, or in own sign.
        result = yoga_summary(chart(70, 250, 310, 130, 10, 220, 100, 190, 10), 30.0)
        raja = [r for r in rows(result, "raja_yoga") if set(r["planets"]) == {"Sun", "Mercury"}]
        assert len(raja) == 1
        assert raja[0]["strength"] == "moderate"
        assert any("parivartana exchange" in t for t in raja[0]["triggers"])


class TestDignityAdjustedStrength:
    def test_raja_yoga_downgraded_for_debilitated_participant(self):
        # Aries lagna; Jupiter (9th lord) debilitated in Capricorn exchanges
        # with Saturn (10th lord) in Sagittarius: moderate -> weak.
        result = yoga_summary(chart(15, 45, 75, 105, 275, 145, 245, 20, 200), 0.0)
        raja = [r for r in rows(result, "raja_yoga") if set(r["planets"]) == {"Jupiter", "Saturn"}]
        assert len(raja) == 1
        assert raja[0]["strength"] == "weak"
        assert any("downgraded: Jupiter debilitated" in n for n in raja[0]["notes"])

    def test_gajakesari_upgraded_for_exalted_jupiter(self):
        # Jupiter exalted in Cancer, 7th (kendra) from Moon in Capricorn:
        # moderate -> strong.
        result = yoga_summary(chart(10, 280, 220, 40, 100, 190, 340, 65, 245), 0.0)
        gaja = one(result, "gaja_kesari_yoga")
        assert gaja["active"] and gaja["strength"] == "strong"
        assert any("upgraded: Jupiter exalted" in n for n in gaja["notes"])

    def test_mahapurusha_dignity_reported_but_not_upgraded(self):
        # Ruchaka: Mars own sign in Aries lagna stays moderate (own/exalted is
        # definitional, so no dignity upgrade is applied).
        result = yoga_summary(chart(20, 50, 5, 75, 95, 145, 185, 250, 70), 0.0)
        ruchaka = one(result, "ruchaka_yoga")
        assert ruchaka["active"] and ruchaka["strength"] == "moderate"
        assert "definitional" in notes_text(ruchaka)
        # Sasa via exaltation is graded strong by definition, not by upgrade.
        sasa = one(result, "sasa_yoga")
        assert sasa["active"] and sasa["strength"] == "strong"
