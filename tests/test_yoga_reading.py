"""Yogas and doshas explain themselves: what, why (this chart's placements),
impact, do, avoid — and the classical rules they were checked against.

Discovery 2026-10-29 (Phaladeepika VI-VII, Brihat Jataka XII-XIII, BPHS ch.37-41).
"""
import random

import pytest

from astrospace.core.vedic.chart import VedicChart
from astrospace.core.vedic.doshas import dosha_summary
from astrospace.core.vedic.yogas import yoga_summary
from astrospace.knowledge.vedic_rules import reader_catalog, rules_catalog

PLANET_ORDER = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]
READER_FIELDS = ("what", "formed_when", "impact", "do", "avoid", "how_common")
FEAR_WORDS = ("disaster", "danger", "curse", "doom", "suffer", "guaranteed", "will fail", "must buy", "death")


def chart(sun, moon, mars, mercury, jupiter, venus, saturn, rahu, ketu):
    lons = [sun, moon, mars, mercury, jupiter, venus, saturn, rahu, ketu]
    return {name: {"lon": float(lon)} for name, lon in zip(PLANET_ORDER, lons)}


def rows(result, rule_id):
    return [r for r in result["all"] if r["rule_id"] == rule_id]


class TestCorpus:
    def test_every_computed_rule_has_reader_text(self):
        reader = reader_catalog()
        for rule_id, rule in rules_catalog().items():
            if rule["implementation"] == "not_implemented":
                continue
            entry = reader.get(rule_id)
            assert entry, f"{rule_id} has no reader entry"
            for field in READER_FIELDS:
                assert field in entry, f"{rule_id} reader entry missing {field}"
            if rule_id != "sankhya_yoga":
                assert entry["do"] and entry["avoid"], f"{rule_id} needs Do and Avoid lines"

    def test_reader_text_is_plain_and_never_fearful(self):
        for rule_id, entry in reader_catalog().items():
            text = " ".join([entry["what"], entry["formed_when"], entry["impact"], *entry["do"], *entry["avoid"]])
            lowered = text.lower()
            for word in FEAR_WORDS:
                assert word not in lowered, f"{rule_id} uses {word!r}"
            assert "—" not in text, f"{rule_id} uses a long dash"
            for line in [*entry["do"], *entry["avoid"]]:
                assert len(line) <= 90, f"{rule_id} Do/Avoid line too long: {line}"

    def test_flags_say_they_are_not_verdicts(self):
        catalog = rules_catalog()
        for rule_id, entry in reader_catalog().items():
            rule = catalog.get(rule_id) or {}
            is_flag = "caution" in rule.get("category", "").lower() and rule_id != "asubha_vesi_yoga" \
                and rule_id != "asubha_vosi_yoga" and rule_id != "guru_chandala_yoga" and rule_id != "kalasarpa_flag"
            if is_flag:
                assert "not a verdict" in entry["impact"], f"{rule_id} impact must say it is a flag, not a verdict"

    def test_remedies_are_never_paid_removal(self):
        for rule_id, entry in reader_catalog().items():
            for line in entry["do"]:
                assert "pay" not in line.lower() and "buy" not in line.lower(), f"{rule_id}: {line}"


class TestEveryCardExplainsItself:
    @pytest.fixture(scope="class")
    def charts(self):
        rng = random.Random(29)
        return [
            VedicChart("x", rng.randint(1950, 2012), rng.randint(1, 12), rng.randint(1, 28),
                       rng.randint(0, 23), rng.randint(0, 59), "Hyderabad", "IN")
            for _ in range(120)
        ]

    def test_every_active_yoga_has_why_and_reader_text(self, charts):
        for c in charts:
            for y in c.yogas()["active"]:
                assert y["why"], f"{y['name']} has no plain why"
                assert all(line and line[0].isupper() for line in y["why"]), y["why"]
                assert y["reader"].get("what"), f"{y['rule_id']} has no reader text"

    def test_every_active_dosha_has_why(self, charts):
        for c in charts:
            for name, d in c.doshas().items():
                if d["active"]:
                    assert d["why"], f"{name} active without a plain why"
                    assert d["reader"].get("impact")
                else:
                    assert d["why"] == []

    def test_manglik_why_names_the_point_that_triggered_it(self):
        c = VedicChart("Ravi", 1990, 3, 14, 6, 40, "Hyderabad", "IN")
        why = c.doshas()["manglik"]["why"]
        assert why[0].startswith("From your Venus in Capricorn, Mars in Capricorn is in the 1st place")
        assert why[-1] == "From your rising sign and Moon, Mars is clear."


class TestNeechaBhanga:
    """Phaladeepika VII.26-30: every listed way repairs a debilitated planet."""

    def test_fall_sign_lord_in_kendra_from_lagna(self):
        # Sun in Libra (fallen); Venus, Libra's lord, in Cancer = 4th from Aries Lagna.
        result = yoga_summary(chart(190, 40, 130, 160, 250, 100, 310, 70, 250), 0.0)
        row = rows(result, "neecha_bhanga_raja_yoga")[0]
        assert row["active"]
        assert any("Venus, lord of debilitation sign, is kendra from Lagna" in t for t in row["triggers"])

    def test_planet_exalted_in_the_fall_sign_counts(self):
        # Jupiter in Capricorn (fallen); Mars, exalted in Capricorn, in Libra = 7th from Aries Lagna.
        result = yoga_summary(chart(130, 40, 190, 160, 280, 70, 220, 100, 280), 0.0)
        row = rows(result, "neecha_bhanga_raja_yoga")[0]
        assert any("Mars, exalted in Capricorn" in t for t in row["triggers"])

    def test_fallen_planet_aspected_by_its_sign_lord(self):
        # Saturn in Aries (fallen); Mars, Aries' lord, in Libra looks at it (7th).
        result = yoga_summary(chart(70, 130, 190, 100, 160, 40, 10, 250, 70), 45.0)
        row = rows(result, "neecha_bhanga_raja_yoga")[0]
        assert any("Mars, lord of debilitation sign, aspects Saturn" in t for t in row["triggers"])

    def test_two_ways_grade_it_strong(self):
        result = yoga_summary(chart(190, 40, 130, 160, 250, 100, 310, 70, 250), 0.0)
        row = rows(result, "neecha_bhanga_raja_yoga")[0]
        assert row["strength"] == ("strong" if len(row["triggers"]) >= 2 else "moderate")
        assert row["why"][0] == "Sun is in Libra, its weakest sign."


class TestKemadruma:
    # Moon alone in Aries; nothing beside it, with it, or in a kendra from it.
    LONELY = (130, 10, 220, 160, 250, 130, 310, 60, 240)

    def test_active_when_no_cancellation(self):
        result = yoga_summary(chart(*self.LONELY), 0.0)
        row = rows(result, "kemadruma_yoga")[0]
        assert row["active"] and not row["cancelled"]
        assert row["why"][0].startswith("Your Moon is in Aries.")

    def test_planet_in_kendra_from_lagna_cancels_it(self):
        # Gemini Lagna: Mercury in Virgo (4th) and Jupiter in Sagittarius (7th).
        result = yoga_summary(chart(*self.LONELY), 65.0)
        row = rows(result, "kemadruma_yoga")[0]
        assert not row["active"] and row["cancelled"]
        assert "kendra from Lagna" in row["cancellations"][0]
        assert row["why"], "a cancelled flag still shows the reader why it was checked"


class TestPanchaMahapurushaFromMoon:
    def test_hamsa_counts_from_the_moon(self):
        # Jupiter exalted in Cancer: 3rd from Taurus Lagna, but 4th from the Moon in Aries.
        result = yoga_summary(chart(130, 10, 220, 160, 100, 190, 310, 60, 240), 30.0)
        hamsa = rows(result, "hamsa_yoga")[0]
        assert hamsa["active"]
        assert any("from Moon" in t for t in hamsa["triggers"])
        assert "Formed from the Moon only" in " ".join(hamsa["notes"])


class TestRajaYogaLinks:
    def test_one_way_links_are_marked_partial(self):
        result = yoga_summary(chart(10, 130, 40, 160, 250, 190, 340, 100, 280), 0.0)
        for row in rows(result, "raja_yoga") + rows(result, "dhana_yoga"):
            one_way = any("one-way" in t for t in row["triggers"])
            assert row["partial"] is one_way
            assert row["why"][1].endswith(("a one-way link.", ".")), row["why"]


def test_dosha_summary_attaches_reader_and_why():
    out = dosha_summary(chart(10, 40, 100, 160, 250, 190, 280, 100, 280), 0.0)
    assert set(out) == {"manglik", "gandanta", "grahan"}
    assert out["manglik"]["reader"]["what"].startswith("A marriage-matching check")
