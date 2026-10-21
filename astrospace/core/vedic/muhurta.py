"""Goal-based muhurta finder: ranks good times for a stated purpose.

The question a reader asks is *"when is a good time to take delivery of my
car?"*, not "list today's Abhijit". So this module scans the hours in which
the purpose can actually happen (a showroom's day, a ceremony's morning, a
journey's any hour), cuts each day into its classical muhurtas (a fifteenth
of the day or night, about 48 minutes), drops the parts covered by Rahu Kalam
and the other avoid-windows, and scores each block on:

* the **block**: Abhijit, Brahma Muhurta, Godhuli, Amrit Kalam, the
  Choghadiya and hora in force, and the rising sign (lagna) where the purpose
  has a traditional preference;
* the **moment's panchang**: weekday, nakshatra, tithi and nitya yoga taken at
  the middle of the block, not at sunrise, so a 22:31 slot is judged on the
  star actually in force then;
* the **person** (or both people, for a marriage): tarabala and chandrabala;
* **special days**: Guru/Ravi Pushya, Amrit Siddhi, Sarvartha Siddhi,
  Dwi/Tripushkar, and the
  festival days a purpose is traditionally done on;
* **season rules** a family priest checks first for the big samskaras:
  Jupiter or Venus combust, adhika masa, Kharmas and Chaturmas.

Design constraints (design_principles.md §4):

* **No health, legal or financial goals.** A "good time to start treatment" or
  "win a case" is a refer-out, not a muhurta. :func:`find` raises for those,
  in the goal slug and in the reader's own typed words.
* **Timing supports intent; it does not guarantee outcome.** Every result
  carries plain reasons and the classical terms behind them, and the payload
  says the decision remains the reader's.
* **Honest emptiness.** If nothing clears the bar the finder says so, and says
  what it left out and why, rather than inventing a "best available" slot.
* **Convention-dependent.** Every table here has regional variants. Results
  carry ``is_convention_dependent`` and an ``observance_note`` naming the rule
  used; season rules can be switched off by the reader.

The weekday/nakshatra tables are the common panchang ones. Muhurta Chintamani,
the standard text, is not yet in the knowledge base; see the Muhurta entry in
the deferred backlog of docs/backend_astro_depth_checklist_2026-08-06.md.
"""
from __future__ import annotations

import re
from datetime import date as date_cls, datetime, timedelta, timezone

import swisseph as swe

from .constants import NAKSHATRAS, NAKSHATRA_SPAN, TITHI_NAMES, VARA_NAMES, YOGA_NAMES
from .panchanga_day import (
    CHANDRABALA_GOOD, DISHA_SHOOL, PANCHAKA_NAKSHATRA_IDX, TARABALA_GOOD,
    TARABALA_NAMES, daily_panchanga, personal_panchanga,
)
from .positions import (
    resolve_location, sidereal_lagna, sidereal_positions, sign_index, sign_name,
    sun_moon_sidereal,
)

# ── Goals ────────────────────────────────────────────────────────────────────
#
#   prefer_vara      weekdays that traditionally suit the purpose
#   prefer_nakshatra nakshatras favoured for it
#   avoid_tithi      tithi numbers (1-15 within a paksha) avoided
#   shun_vara        weekdays the text rules out: marked down, not dropped
#   avoid_lagna      rising signs ruled out even when the lagna type fits
#   source           the Muhurta Chintamani verses the lists follow (1907
#                    Venkateshwar Press print); None where the book gives no
#                    rule for the purpose and common panchang practice is used
#   hours            (start, end) local hours the purpose can happen in; an
#                    end above 24 runs past midnight. None is any hour.
#   hours_note       what the hours leave out, in plain words
#   predawn          Brahma Muhurta is offered even when hours start later
#   shukla           waxing fortnight preferred
#   season           season rules observed by default (see _season_blocks)
#   lagna            rising-sign type preferred: fixed / movable / dual
#   hora             planet whose hora helps
#   festivals        festival slugs this purpose is traditionally done on
#   special          special-day yogas give a strong lift (purchases)
#   panchaka         Panchaka is avoided
#   whose            whose chart the screen should ask for
#   major            a big life event: Chandrashtama rules the day out
#   category         how the picker groups it

RIKTA_TITHIS = frozenset({4, 9, 14})

_ERRANDS = "Only times between {start} and {end} are shown, since {places} are closed outside them."
_SEASON_SAMSKARA = frozenset({"guru_asta", "shukra_asta", "adhika", "kharmas", "chaturmas"})
_SEASON_LIGHT = frozenset({"guru_asta", "shukra_asta", "adhika"})

_GENERAL_NAKSHATRAS = ["Ashwini", "Rohini", "Mrigashira", "Punarvasu", "Pushya",
                       "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Anuradha",
                       "Uttara Ashadha", "Shravana", "Dhanishta",
                       "Uttara Bhadrapada", "Revati"]
_SAMSKARA_NAKSHATRAS = ["Ashwini", "Rohini", "Mrigashira", "Punarvasu", "Pushya",
                        "Hasta", "Chitra", "Swati", "Anuradha", "Shravana", "Revati"]
# Muhurta Chintamani's star groups (chapter 1).
_DHRUVA = ["Rohini", "Uttara Phalguni", "Uttara Ashadha", "Uttara Bhadrapada"]
_MRIDU = ["Mrigashira", "Chitra", "Anuradha", "Revati"]
_KSHIPRA = ["Ashwini", "Pushya", "Hasta"]
_CHARA = ["Punarvasu", "Swati", "Shravana", "Dhanishta", "Shatabhisha"]
_THREE_PURVAS = ["Purva Phalguni", "Purva Ashadha", "Purva Bhadrapada"]


def _stars(*groups) -> list[str]:
    """Star groups and single stars, in zodiac order, without repeats."""
    names = {n for g in groups for n in ([g] if isinstance(g, str) else g)}
    unknown = names - set(NAKSHATRAS)
    assert not unknown, unknown
    return [n for n in NAKSHATRAS if n in names]


_SAMSKARA_STARS = _stars(_MRIDU, _DHRUVA, _KSHIPRA, _CHARA)
_VIVAHA_STARS = _stars("Mrigashira", "Hasta", "Moola", "Anuradha", "Magha",
                       "Rohini", "Revati", "Uttara Phalguni", "Uttara Ashadha",
                       "Uttara Bhadrapada", "Swati")
_MC = "Muhurta Chintamani {} (1907 Venkateshwar Press print)"

GOALS: dict[str, dict] = {
    # ── Purchases and errands ──
    "buy_vehicle": {
        "category": "purchase",
        "label": "Buy or take delivery of a vehicle",
        "prefer_vara": ["Monday", "Wednesday", "Thursday", "Friday"],
        # 2.16 (buying: Revati, Shatabhisha, Ashwini, Swati, Shravana,
        # Chitra) and 2.18 (a mount to ride: kshipra, Revati, Mrigashira,
        # Swati, Shatabhisha, Punarvasu; not rikta, not Tuesday).
        "prefer_nakshatra": _stars(_KSHIPRA, "Revati", "Mrigashira", "Swati",
                                   "Shatabhisha", "Punarvasu", "Shravana", "Chitra"),
        "avoid_tithi": RIKTA_TITHIS,
        "shun_vara": ["Tuesday"],
        "hours": (9, 19),
        "hours_note": _ERRANDS.format(start="9 am", end="7 pm", places="showrooms"),
        "hora": "Venus",
        "festivals": ["dhanteras", "akshaya_tritiya", "vijayadashami"],
        "special": True,
        "source": _MC.format("2.16, 2.18"),
    },
    "buy_gold": {
        "category": "purchase",
        "label": "Buy gold or jewellery",
        "prefer_vara": ["Sunday", "Monday", "Wednesday", "Thursday", "Friday"],
        # 2.19 (ornaments: Tripushkar, chara, kshipra, dhruva, Revati; never
        # the fierce or sharp stars) and 2.16 (buying) for Chitra.
        "prefer_nakshatra": _stars(_CHARA, _KSHIPRA, _DHRUVA, "Revati", "Chitra"),
        "avoid_tithi": RIKTA_TITHIS,
        "hours": (10, 21),
        "hours_note": _ERRANDS.format(start="10 am", end="9 pm", places="jewellery shops"),
        "hora": "Venus",
        "festivals": ["akshaya_tritiya", "dhanteras"],
        "special": True,
        "source": _MC.format("2.16, 2.19"),
    },
    "buy_property_gold": {
        "category": "purchase",
        "label": "Buy property",
        "prefer_vara": ["Thursday", "Friday"],
        "prefer_nakshatra": ["Rohini", "Pushya", "Uttara Phalguni", "Uttara Ashadha",
                             "Uttara Bhadrapada", "Anuradha", "Revati", "Mrigashira"],
        "avoid_tithi": RIKTA_TITHIS,
        "hours": (9, 19),
        "hours_note": _ERRANDS.format(start="9 am", end="7 pm", places="offices and banks"),
        "lagna": "fixed",
        "hora": "Jupiter",
        "festivals": ["akshaya_tritiya"],
        "special": True,
    },
    "property_registration": {
        "category": "purchase",
        "label": "Register property",
        "prefer_vara": ["Monday", "Wednesday", "Thursday", "Friday"],
        "prefer_nakshatra": ["Rohini", "Mrigashira", "Pushya", "Uttara Phalguni",
                             "Hasta", "Chitra", "Anuradha", "Uttara Ashadha",
                             "Shravana", "Uttara Bhadrapada", "Revati"],
        "avoid_tithi": RIKTA_TITHIS,
        "avoid_vara": ["Sunday"],
        "hours": (10.5, 17),
        "hours_note": _ERRANDS.format(start="10:30 am", end="5 pm",
                                      places="sub-registrar offices"),
        "lagna": "fixed",
        "special": True,
    },
    "sign_contract": {
        "category": "work",
        "label": "Sign a contract",
        # 2.42 is the nearest rule the book has: sandhana, making an alliance
        # or a friendship, on Pushya, Anuradha or Purva Phalguni, on a
        # benefic weekday, with Venus in or aspecting the lagna. (Its 8th and
        # 12th lunar days are preferred there; rikta days stay avoided.)
        "prefer_vara": ["Monday", "Wednesday", "Thursday", "Friday"],
        "prefer_nakshatra": _stars("Pushya", "Purva Phalguni", "Anuradha"),
        "avoid_tithi": RIKTA_TITHIS,
        "source": _MC.format("2.42"),
        "hours": (9, 19),
        "hours_note": _ERRANDS.format(start="9 am", end="7 pm", places="offices"),
        "hora": "Mercury",
    },
    "start_venture": {
        "category": "work",
        "label": "Open a shop or start a business",
        "prefer_vara": ["Wednesday", "Thursday", "Friday"],
        # 2.17: Anuradha, dhruva and kshipra; not rikta, not Tuesday, not
        # with Aquarius rising.
        "prefer_nakshatra": _stars(_DHRUVA, _KSHIPRA, "Anuradha"),
        "avoid_tithi": RIKTA_TITHIS,
        "shun_vara": ["Tuesday"],
        "hours": (7, 20),
        "hours_note": "Only times between 7 am and 8 pm are shown, when a shop or office opening can be held.",
        "lagna": "fixed",
        "avoid_lagna": {10: "Aquarius rising is avoided for opening a shop"},
        "source": _MC.format("2.17"),
        "hora": "Mercury",
        "festivals": ["akshaya_tritiya", "dhanteras", "diwali", "vijayadashami"],
        "special": True,
    },
    "join_job": {
        "category": "work",
        "label": "Join a new job",
        # 2.26: entering service on kshipra stars or Anuradha, on a
        # Wednesday, Friday, Sunday or Thursday.
        "prefer_vara": ["Sunday", "Wednesday", "Thursday", "Friday"],
        "prefer_nakshatra": _stars(_KSHIPRA, "Anuradha"),
        "source": _MC.format("2.26"),
        "avoid_tithi": RIKTA_TITHIS,
        "hours": (8, 19),
        "hours_note": _ERRANDS.format(start="8 am", end="7 pm", places="offices"),
        "hora": "Sun",
    },
    "move_rented_home": {
        "category": "home",
        "label": "Move into a rented home",
        "prefer_vara": ["Monday", "Wednesday", "Thursday", "Friday"],
        # 13.2: entering a house already lived in adds Shatabhisha, Pushya,
        # Swati and Dhanishta to the mridu and dhruva stars.
        "prefer_nakshatra": _stars(_MRIDU, _DHRUVA, "Shatabhisha", "Pushya",
                                   "Swati", "Dhanishta"),
        "avoid_tithi": RIKTA_TITHIS | {15},
        "shun_vara": ["Sunday", "Tuesday"],
        "source": _MC.format("13.1-13.2"),
        "hours": (6, 20),
        "hours_note": "Only times between 6 am and 8 pm are shown, when a move can be made.",
    },
    # ── Home ──
    "griha_pravesha": {
        "category": "home",
        "label": "Griha Pravesha / house warming",
        "prefer_vara": ["Monday", "Wednesday", "Thursday", "Friday"],
        # 13.1: mridu and dhruva stars; not Sunday or Tuesday.
        "prefer_nakshatra": _stars(_MRIDU, _DHRUVA),
        "shun_vara": ["Sunday", "Tuesday"],
        "source": _MC.format("13.1-13.4"),
        "avoid_tithi": RIKTA_TITHIS | {15},
        "hours": (6, 13),
        "hours_note": "Only morning times are shown (from Brahma Muhurta to 1 pm), when griha pravesha is usually done.",
        "predawn": True,
        "shukla": True,
        "season": _SEASON_SAMSKARA,
        "lagna": "fixed",
        "panchaka": True,
        "whose": "family",
        "major": True,
    },
    "bhoomi_puja": {
        "category": "home",
        "label": "Bhoomi puja / start building",
        "prefer_vara": ["Monday", "Wednesday", "Thursday", "Friday"],
        # 12.15, 12.18: dhruva, mridu, Shatabhisha, Swati, Dhanishta, Hasta,
        # Pushya; not Sunday or Tuesday; the commentary also rules out the
        # first and eighth lunar days.
        "prefer_nakshatra": _stars(_DHRUVA, _MRIDU, "Shatabhisha", "Swati",
                                   "Dhanishta", "Hasta", "Pushya"),
        "avoid_tithi": RIKTA_TITHIS | {1, 8, 15},
        "shun_vara": ["Sunday", "Tuesday"],
        "source": _MC.format("12.15, 12.18"),
        "hours": (6, 12),
        "hours_note": "Only morning times (6 am to noon) are shown, when bhoomi puja is usually done.",
        "shukla": True,
        "season": _SEASON_SAMSKARA,
        "lagna": "fixed",
        "panchaka": True,
        "whose": "family",
        "major": True,
    },
    # ── Family ceremonies ──
    "marriage_related": {
        "category": "family",
        "label": "Wedding",
        # 6.53: Mrigashira, Hasta, Moola, Anuradha, Magha, Rohini, Revati,
        # the three Uttaras and Swati, free of vedha, on a benefic weekday;
        # not rikta or Amavasya (the full moon is allowed). 6.13 gives the
        # months, which the season rules already cover.
        "prefer_vara": ["Monday", "Wednesday", "Thursday", "Friday"],
        "prefer_nakshatra": _VIVAHA_STARS,
        "avoid_tithi": RIKTA_TITHIS,  # Amavasya is always avoided
        "source": _MC.format("6.13, 6.53"),
        "hours": None,
        "season": _SEASON_SAMSKARA,
        "lagna": "marriage",
        "whose": "couple",
        "major": True,
    },
    "engagement": {
        "category": "family",
        "label": "Engagement",
        # 6.10-6.11: choosing the bride and the groom (sagai, vagdana) on the
        # wedding stars and also Uttara Ashadha, Swati, Shravana, the three
        # Purvas, Anuradha, Dhanishta and Krittika, on a benefic day.
        "prefer_vara": ["Monday", "Wednesday", "Thursday", "Friday"],
        "prefer_nakshatra": _stars(_VIVAHA_STARS, "Shravana", _THREE_PURVAS,
                                   "Dhanishta", "Krittika"),
        "source": _MC.format("6.10-6.11"),
        "avoid_tithi": RIKTA_TITHIS,
        "hours": (9, 21),
        "hours_note": "Only times between 9 am and 9 pm are shown, when families usually meet.",
        "season": _SEASON_LIGHT,
        "hora": "Venus",
        "whose": "couple",
    },
    "seemantham": {
        "category": "family",
        "label": "Seemantham / baby shower",
        # 5.8: Thursday, Tuesday or Sunday; Mrigashira, Pushya, Moola,
        # Shravana, Hasta, Punarvasu, or else dhruva stars and Revati; not
        # the 4th, 6th, 8th, 9th, 12th, 14th or a new or full moon.
        "prefer_vara": ["Sunday", "Tuesday", "Thursday"],
        "prefer_nakshatra": _stars("Mrigashira", "Pushya", "Moola", "Shravana",
                                   "Hasta", "Punarvasu", _DHRUVA, "Revati"),
        "avoid_tithi": RIKTA_TITHIS | {6, 8, 12, 15},
        "source": _MC.format("5.8"),
        "hours": (7, 13),
        "hours_note": "Only morning times (7 am to 1 pm) are shown, when the ceremony is usually held.",
        "shukla": True,
        "whose": "mother",
    },
    "namakarana": {
        "category": "family",
        "label": "Namakarana / naming",
        "prefer_vara": ["Monday", "Wednesday", "Thursday", "Friday"],
        # 5.11: mridu, dhruva, kshipra and chara stars.
        "prefer_nakshatra": _SAMSKARA_STARS,
        "source": _MC.format("5.11"),
        "avoid_tithi": RIKTA_TITHIS | {15},
        "hours": (7, 13),
        "hours_note": "Only morning times (7 am to 1 pm) are shown, when relatives can gather.",
        "whose": "child",
    },
    "annaprashana": {
        "category": "family",
        "label": "Annaprashana",
        "prefer_vara": ["Monday", "Wednesday", "Thursday", "Friday"],
        # 5.17: fixed, soft, light and moving stars; not the 1st, 4th, 6th,
        # 8th, 9th, 11th, 12th, 14th or a new or full moon; not Saturday,
        # Tuesday or Sunday.
        "prefer_nakshatra": _SAMSKARA_STARS,
        "avoid_tithi": RIKTA_TITHIS | {1, 6, 8, 11, 12, 15},
        "shun_vara": ["Sunday", "Tuesday", "Saturday"],
        "source": _MC.format("5.17"),
        "hours": (7, 13),
        "hours_note": "Only morning times (7 am to 1 pm) are shown, when the first meal is usually given.",
        "shukla": True,
        "whose": "child",
    },
    "mundan": {
        "category": "family",
        "label": "Mundan / first haircut",
        "prefer_vara": ["Monday", "Wednesday", "Thursday", "Friday"],
        "prefer_nakshatra": ["Ashwini", "Mrigashira", "Punarvasu", "Pushya",
                             "Hasta", "Chitra", "Swati", "Jyeshtha", "Shravana",
                             "Dhanishta", "Shatabhisha", "Revati"],
        # 5.29: mridu, chara, laghu and Jyeshtha; not rikta, the 1st, the 6th
        # or a parva day.
        "avoid_tithi": RIKTA_TITHIS | {1, 6, 15},
        "source": _MC.format("5.29"),
        "hours": (6, 12),
        "hours_note": "Only morning times (6 am to noon) are shown, when mundan is usually done.",
        "shukla": True,
        "season": _SEASON_SAMSKARA,
        "whose": "child",
    },
    "karnavedha": {
        "category": "family",
        "label": "Karnavedha / ear piercing",
        "prefer_vara": ["Monday", "Wednesday", "Thursday", "Friday"],
        "prefer_nakshatra": ["Ashwini", "Mrigashira", "Punarvasu", "Pushya",
                             "Hasta", "Chitra", "Anuradha", "Shravana",
                             "Dhanishta", "Revati"],
        "avoid_tithi": RIKTA_TITHIS | {15},
        "hours": (8, 17),
        "hours_note": "Only daytime (8 am to 5 pm) is shown.",
        # 5.24 also leaves out Chaitra, Pausha and Hari's sleep (Chaturmas).
        "season": frozenset({"kharmas", "chaturmas"}),
        "source": _MC.format("5.24"),
        "whose": "child",
    },
    "upanayana": {
        "category": "family",
        "label": "Upanayana",
        # 5.40: kshipra, dhruva, chara and mridu stars, Ashlesha, Moola, the
        # three Purvas and Ardra; Sunday, Wednesday, Thursday, Friday or
        # Monday; the 2nd, 3rd, 5th, 10th, 11th or 12th (the first third of
        # the dark half is also allowed, which a 1-15 tithi set cannot say);
        # never the afternoon.
        "prefer_vara": ["Sunday", "Monday", "Wednesday", "Thursday", "Friday"],
        "prefer_nakshatra": _stars(_SAMSKARA_STARS, "Ashlesha", "Moola",
                                   _THREE_PURVAS, "Ardra"),
        "avoid_tithi": RIKTA_TITHIS | {6, 7, 8, 13, 15},
        "source": _MC.format("5.39-5.40"),
        "hours": (6, 13),
        "hours_note": "Only morning times (6 am to 1 pm) are shown, when upanayana is held.",
        "shukla": True,
        "season": _SEASON_SAMSKARA,
        "hora": "Jupiter",
        "whose": "child",
        "major": True,
    },
    "vidyarambha": {
        "category": "family",
        "label": "Vidyarambha / start learning",
        # 5.37 (a child's first letters): laghu stars, Shravana, Swati,
        # Revati, Punarvasu, Ardra, Chitra, Anuradha; Monday, Wednesday,
        # Thursday or Friday; the 2nd, 3rd, 5th, 6th, 10th, 11th or 12th.
        "prefer_vara": ["Monday", "Wednesday", "Thursday", "Friday"],
        "prefer_nakshatra": _stars(_KSHIPRA, "Shravana", "Swati", "Revati",
                                   "Punarvasu", "Ardra", "Chitra", "Anuradha"),
        "avoid_tithi": RIKTA_TITHIS | {1, 7, 8, 13, 15},
        "source": _MC.format("5.37"),
        "hours": (6, 12),
        "hours_note": "Only morning times (6 am to noon) are shown, when learning is traditionally begun.",
        "hora": "Mercury",
        "festivals": ["vijayadashami", "vasant_panchami"],
        "whose": "child",
    },
    # ── Travel and practice ──
    "start_journey": {
        "category": "travel",
        "label": "Start a journey",
        "prefer_vara": ["Monday", "Wednesday", "Thursday", "Friday"],
        # 11.9: these nine stars; not the 6th, 8th, 12th, rikta, new or full
        # moon (nor the bright 1st, which a 1-15 tithi set cannot say).
        "prefer_nakshatra": ["Ashwini", "Mrigashira", "Punarvasu", "Pushya",
                             "Hasta", "Anuradha", "Shravana", "Dhanishta", "Revati"],
        "avoid_tithi": RIKTA_TITHIS | {6, 8, 12, 15},
        "source": _MC.format("11.9"),
        "hours": None,
        "lagna": "movable",
        "travel": True,
    },
    "start_sadhana": {
        "category": "practice",
        "label": "Start a vrat, japa or practice",
        "prefer_vara": ["Monday", "Wednesday", "Thursday", "Friday", "Sunday"],
        "prefer_nakshatra": _SAMSKARA_NAKSHATRAS,
        "avoid_tithi": frozenset(),
        "hours": (5, 10),
        "hours_note": "Only early morning (Brahma Muhurta to 10 am) is shown, the traditional time to begin a practice.",
        "predawn": True,
        "shukla": True,
    },
    "general": {
        # A typed purpose is nearly always an errand in the world (a delivery,
        # a purchase, a meeting), so it keeps to the day and is scored on the
        # weekdays and nakshatras held good for most auspicious work.
        "category": "other",
        "label": "Something else",
        "prefer_vara": ["Monday", "Wednesday", "Thursday", "Friday"],
        "prefer_nakshatra": _GENERAL_NAKSHATRAS,
        "avoid_tithi": RIKTA_TITHIS,
        "hours": (8, 20),
        "hours_note": "Only times between 8 am and 8 pm are shown, since shops, showrooms, offices and banks are closed outside them.",
    },
}

# Wedding ceremonies are held in the morning in most of the south and in the
# evening or night (Godhuli lagna onward) across much of the north; the
# reader picks, and neither is marked down.
CEREMONY_HOURS = {
    "day": ((6, 18), "Only daytime ceremonies (6 am to 6 pm) are shown."),
    "night": ((17, 30), "Only evening and night ceremonies (5 pm to 6 am) are shown."),
}

# A typed "Something else" purpose that plainly names a goal with its own
# rules is scored by those rules. First match wins; the specific goes ahead
# of the broad ("car delivery" is a vehicle, not a journey).
INTENT_GOALS: list[tuple[str, str]] = [
    (r"\b(car|cars|vehicle|bike|motor ?bike|motorcycle|scooter|scooty|"
     r"two[- ]wheeler|tractor|truck|lorry|suv|jeep|auto ?rickshaw|ev)\b", "buy_vehicle"),
    (r"\b(house ?warming|griha|gruha|gr[iu]hapravesh?\w*)\b", "griha_pravesha"),
    (r"\b(bhoomi|bhumi|foundation|construction|build(ing)? (a |the |our )?house)\b", "bhoomi_puja"),
    (r"\b(engagement|nischitartham|betrothal|roka|sagai)\b", "engagement"),
    (r"\b(wedding|marriage|vivah|kalyanam)\b", "marriage_related"),
    (r"\b(seemantham|seemantham|valaikappu|godh bharai|baby shower)\b", "seemantham"),
    (r"\b(naming|namakaran\w*|cradle)\b", "namakarana"),
    (r"\b(annaprashan\w*|first (meal|feeding|rice))\b", "annaprashana"),
    (r"\b(mundan\w*|tonsure|first haircut|chudakarana|chaula)\b", "mundan"),
    (r"\b(ear piercing|karnavedh\w*|karnavedha)\b", "karnavedha"),
    (r"\b(upanayan\w*|thread ceremony|janeu|poonal)\b", "upanayana"),
    (r"\b(akshar\w*|vidyarambh\w*|start school|school admission)\b", "vidyarambha"),
    (r"\b(gold|jewel\w*|silver|diamond)\b", "buy_gold"),
    (r"\b(registration|register|registry)\b", "property_registration"),
    (r"\b(rent\w*|shift\w*|moving|move house|move home)\b", "move_rented_home"),
    (r"\b(property|land|plot|flat|apartment|villa|house)\b", "buy_property_gold"),
    (r"\b(join\w*|new job|offer letter)\b", "join_job"),
    (r"\b(contract|agreement|deed|sign|signing)\b", "sign_contract"),
    (r"\b(shop|store|business|office|company|startup|venture|opening|launch)\b", "start_venture"),
    (r"\b(vrat\w*|japa|sadhana|mantra|puja|fast)\b", "start_sadhana"),
    (r"\b(journey|travel|trip|pilgrimage|yatra|flight)\b", "start_journey"),
]

NIGHT_DROPPED_NOTE = GOALS["general"]["hours_note"]

# Intents that must never be answered with a muhurta. These refer out instead.
# Matched as whole words in typed text (a courtyard is not a court case).
EXCLUDED_INTENTS = {
    "medical": "health",
    "treatment": "health",
    "surgery": "health",
    "surgeries": "health",
    "operation": "health",
    "c-section": "health",
    "c section": "health",
    "caesarean": "health",
    "cesarean": "health",
    "hospital": "health",
    "ivf": "health",
    "chemo": "health",
    "dialysis": "health",
    "delivery date": "health",
    "baby delivery": "health",
    "litigation": "legal",
    "court": "legal",
    "lawsuit": "legal",
    "hearing": "legal",
    "bail": "legal",
    "divorce": "legal",
    "investment": "financial",
    "invest": "financial",
    "trading": "financial",
    "shares": "financial",
    "stocks": "financial",
    "crypto": "financial",
    "loan": "financial",
    "mutual fund": "financial",
}


class ExcludedGoalError(ValueError):
    """Raised for intents the product refers out rather than timing."""

    def __init__(self, domain: str):
        self.domain = domain
        # Reader-facing: this sentence is what the app's refer-out card shows.
        super().__init__(
            f"We don't pick times for {domain} decisions. Please take those to "
            "a qualified professional, who can weigh what a chart cannot."
        )


# ── Scoring ──────────────────────────────────────────────────────────────────
# Points for a block, then for the moment and the person; shown out of 100
# against a strong, reachable window (Abhijit or a named window in an Amrit
# choghadiya, on a preferred weekday and nakshatra, both strengths good):
# 20 + 14 + 8 + 4 + 10 + 12 + 10 + 8 = 86 points is 100.

_BLOCK_BASE = 20
_FULL_MARKS = 86
_MIN_SCORE = 55          # below this a block is not offered at all
_GOOD_SCORE = 68
_BEST_SCORE = 82
_MIN_USABLE_MINUTES = 20
_MAX_PER_DAY = 2
_MAX_MERGE_BLOCKS = 3

QUALITY_WORDS = {"best": "Excellent", "good": "Good", "workable": "Usable"}

# Kept for callers and tests that still read named windows' standing.
_WINDOW_BASE = {
    "Abhijit Muhurta": 34,
    "Amrit Kalam": 32,
    "Brahma Muhurta": 26,
    "Godhuli": 20,
}

_CHOGHADIYA_POINTS = {"Amrit": 8, "Shubh": 6, "Labh": 6, "Chal": 0,
                      "Udveg": -6, "Kaal": -6, "Rog": -6}

_FIXED_SIGNS, _MOVABLE_SIGNS, _DUAL_SIGNS = {1, 4, 7, 10}, {0, 3, 6, 9}, {2, 5, 8, 11}
_LAGNA_TYPES = {"fixed": (_FIXED_SIGNS, "a fixed sign, for something meant to last"),
                "movable": (_MOVABLE_SIGNS, "a moving sign, good for setting out"),
                "dual": (_DUAL_SIGNS, "a dual sign")}
_MALEFICS = ("Sun", "Mars", "Saturn", "Rahu", "Ketu")

# Nitya yogas avoided for beginnings.
_BAD_YOGAS = {"Vyatipata", "Vaidhriti"}

# Special days from weekday + nakshatra (and tithi for the Pushkar yogas).
# Amrit Siddhi follows the table in the Muhurta Chintamani commentary (1907
# print, p. 12), which pairs Monday with Shravana; most printed panchangs
# pair it with Mrigashira, so Monday takes either.
_AMRIT_SIDDHI = {"Sunday": {"Hasta"}, "Monday": {"Mrigashira", "Shravana"},
                 "Tuesday": {"Ashwini"}, "Wednesday": {"Anuradha"},
                 "Thursday": {"Pushya"}, "Friday": {"Revati"}, "Saturday": {"Rohini"}}
# Sarvartha Siddhi, "for every purpose": Muhurta Chintamani 1.28-29, as the
# verse gives it. The Hindi commentary's Friday has Purva Phalguni for
# Shravana, and its Wednesday line is garbled in the print; the verse wins.
_SARVARTHA_SIDDHI = {
    "Sunday": {"Hasta", "Moola", "Uttara Phalguni", "Uttara Ashadha",
               "Uttara Bhadrapada", "Pushya", "Ashwini"},
    "Monday": {"Shravana", "Rohini", "Mrigashira", "Pushya", "Anuradha"},
    "Tuesday": {"Ashwini", "Uttara Bhadrapada", "Krittika", "Ashlesha"},
    "Wednesday": {"Rohini", "Anuradha", "Hasta", "Krittika", "Mrigashira"},
    "Thursday": {"Revati", "Anuradha", "Ashwini", "Punarvasu", "Pushya"},
    "Friday": {"Revati", "Anuradha", "Ashwini", "Punarvasu", "Shravana"},
    "Saturday": {"Shravana", "Rohini", "Swati"},
}
_PUSHKAR_VARAS = {"Sunday", "Tuesday", "Saturday"}
_BHADRA_TITHIS = {2, 7, 12}
_TRIPUSHKAR_NAKS = {"Krittika", "Punarvasu", "Uttara Phalguni", "Vishakha",
                    "Uttara Ashadha", "Purva Bhadrapada"}
_DWIPUSHKAR_NAKS = {"Mrigashira", "Chitra", "Dhanishta"}

FESTIVAL_NAMES = {"akshaya_tritiya": "Akshaya Tritiya", "dhanteras": "Dhanteras",
                  "vijayadashami": "Vijayadashami", "vasant_panchami": "Vasant Panchami",
                  "diwali": "Diwali"}

SEASON_TEXT = {
    "guru_asta": ("Jupiter is too close to the Sun (Guru asta)",
                  "while Jupiter is too close to the Sun to be seen (Guru asta)"),
    "shukra_asta": ("Venus is too close to the Sun (Shukra asta)",
                    "while Venus is too close to the Sun to be seen (Shukra asta)"),
    "adhika": ("an extra lunar month (adhika masa)",
               "in the extra lunar month (adhika masa), when new samskaras are put off"),
    "kharmas": ("Kharmas (Sun in Sagittarius or Pisces)",
                "in Kharmas, while the Sun is in Sagittarius or Pisces"),
    "chaturmas": ("Chaturmas",
                  "in Chaturmas, the four months from Devshayani to Prabodhini Ekadashi"),
}

_DIRECTIONS = {"north", "south", "east", "west"}

OBSERVANCE_NOTE = (
    "Rules used: weekday, nakshatra and tithi at the time of each slot, with "
    "the lists for each purpose taken from the classical muhurta texts; Rahu "
    "Kalam, Yamaganda, Gulika, Durmuhurta, Varjya and Bhadra cut out; your "
    "tarabala and chandrabala. Muhurta tables differ by region and family "
    "tradition, and some families also avoid particular weekdays or months. "
    "If you follow a family priest's panchang, theirs comes first."
)


def _base_for(name: str) -> int:
    for prefix, base in _WINDOW_BASE.items():
        if name.startswith(prefix):
            return base
    return 18


def _overlaps(a_start: str, a_end: str, b_start: str, b_end: str) -> bool:
    """True when two ISO local-time ranges intersect."""
    return a_start < b_end and b_start < a_end


def _clear_span(window: dict, inauspicious: list[dict]) -> tuple[datetime, datetime] | None:
    """Largest part of ``window`` not covered by any inauspicious window."""
    start = datetime.fromisoformat(window["start_iso"])
    end = datetime.fromisoformat(window["end_iso"])
    blocks = sorted(
        (datetime.fromisoformat(b["start_iso"]), datetime.fromisoformat(b["end_iso"]))
        for b in inauspicious
        if _overlaps(window["start_iso"], window["end_iso"], b["start_iso"], b["end_iso"])
    )
    free: list[tuple[datetime, datetime]] = []
    cursor = start
    for b_start, b_end in blocks:
        if b_start > cursor:
            free.append((cursor, min(b_start, end)))
        cursor = max(cursor, b_end)
        if cursor >= end:
            break
    if cursor < end:
        free.append((cursor, end))
    if not free:
        return None
    best = max(free, key=lambda f: f[1] - f[0])
    if (best[1] - best[0]) < timedelta(minutes=_MIN_USABLE_MINUTES):
        return None
    return best


DAY_STARTS, DAY_ENDS = 6, 21  # local hours


def _is_night(start: datetime, end: datetime) -> bool:
    """A window any part of which falls before 06:00 or after 21:00 local."""
    if end.date() != start.date():
        return True
    return start.hour < DAY_STARTS or (end.hour, end.minute) > (DAY_ENDS, 0)


def _excluded_domain(text: str, *, whole_words: bool) -> str | None:
    lowered = (text or "").lower().replace("_", " ")
    for token, domain in EXCLUDED_INTENTS.items():
        # Whole words, with room for a plural: "courts", not "courtyard".
        if (re.search(rf"\b{re.escape(token)}\w{{0,2}}\b", lowered) if whole_words
                else token in lowered):
            return domain
    return None


def goal_for_intent(intent: str | None) -> str | None:
    """The goal a typed purpose names, or None when it names none."""
    lowered = (intent or "").lower()
    for pattern, slug in INTENT_GOALS:
        if re.search(pattern, lowered):
            return slug
    return None


# ── The moment ───────────────────────────────────────────────────────────────

def _jd(moment: datetime) -> float:
    utc = moment.astimezone(timezone.utc)
    return swe.julday(utc.year, utc.month, utc.day,
                      utc.hour + utc.minute / 60.0 + utc.second / 3600.0)


def _tithi_name(index: int) -> str:
    if index == 14:
        return "Purnima"
    if index == 29:
        return "Amavasya"
    return f"{TITHI_NAMES[index % 15]} {'Shukla' if index < 15 else 'Krishna'}"


def _moment_facts(moment: datetime) -> dict:
    """Panchang elements in force at one instant."""
    sun, moon = sun_moon_sidereal(_jd(moment))
    nak = min(int(moon / NAKSHATRA_SPAN), 26)
    tithi_index = min(int(((moon - sun) % 360.0) / 12.0), 29)
    yoga = min(int(((sun + moon) % 360.0) / NAKSHATRA_SPAN), 26)
    return {
        "nakshatra_index": nak,
        "nakshatra": NAKSHATRAS[nak],
        "tithi_index": tithi_index,
        "tithi_number": tithi_index % 15 + 1,
        "tithi": _tithi_name(tithi_index),
        "paksha": "Shukla" if tithi_index < 15 else "Krishna",
        "yoga": YOGA_NAMES[yoga],
        "moon_sign": sign_index(moon),
        "sun_sign": sign_index(sun),
    }


def _tara(nak_index: int, janma_nak: int) -> str:
    return TARABALA_NAMES[(nak_index - janma_nak) % 27 % 9]


def _person_factors(facts: dict, person: dict, label: str,
                    plus: list, minus: list, terms: list) -> tuple[int, bool]:
    """Tarabala and chandrabala for one person. Returns (points, chandrashtama)."""
    points = 0
    who = "your" if label == "you" else f"{label}'s"
    tara = _tara(facts["nakshatra_index"], person["nak"])
    if tara in TARABALA_GOOD:
        points += 10 if label == "you" else 5
        plus.append(f"The star of the moment is kind to {who} birth star")
    else:
        points -= 10 if label == "you" else 5
        minus.append(f"The star of the moment is not kind to {who} birth star")
    terms.append(f"Tarabala ({label}): {tara}")
    if tara == "Janma":
        points -= 8
        minus.append(f"It is {who} birth star, which people avoid for big starts")
    house = (facts["moon_sign"] - person["rashi"]) % 12 + 1
    chandrashtama = house == 8
    if chandrashtama:
        points -= 20
        minus.append(f"The Moon is in a hard place for {label if label != 'you' else 'you'} (Chandrashtama)")
    elif house in CHANDRABALA_GOOD:
        points += 8 if label == "you" else 4
        plus.append(f"The Moon is well placed for {label if label != 'you' else 'you'}")
    terms.append(f"Chandrabala ({label}): Moon {house} from birth Moon sign")
    return points, chandrashtama


def _special_days(vara: str, facts: dict) -> list[str]:
    nak, tithi = facts["nakshatra"], facts["tithi_number"]
    found = []
    if nak == "Pushya" and vara == "Thursday":
        found.append("Guru Pushya")
    if nak == "Pushya" and vara == "Sunday":
        found.append("Ravi Pushya")
    if nak in _AMRIT_SIDDHI.get(vara, ()) and "Guru Pushya" not in found:
        found.append("Amrit Siddhi")
    if vara in _PUSHKAR_VARAS and tithi in _BHADRA_TITHIS:
        if nak in _TRIPUSHKAR_NAKS:
            found.append("Tripushkar")
        elif nak in _DWIPUSHKAR_NAKS:
            found.append("Dwipushkar")
    # The broadest of the weekday-star pairings; named only when nothing
    # stronger already covers the day.
    if not found and nak in _SARVARTHA_SIDDHI.get(vara, ()):
        found.append("Sarvartha Siddhi")
    return found


# ── Season rules ─────────────────────────────────────────────────────────────

def _in_chaturmas(masa: str, paksha: str, tithi_number: int) -> bool:
    """Devshayani Ekadashi (Ashadha Shukla 11) to Prabodhini (Kartika Shukla 11), amanta."""
    base = masa.removeprefix("Adhika ")
    if base in ("Shravana", "Bhadrapada", "Ashwina"):
        return True
    if base == "Ashadha" and paksha == "Shukla" and tithi_number >= 11:
        return True
    if base == "Kartika" and paksha == "Shukla" and tithi_number <= 11:
        return True
    return False


def _season_blocks(day: dict, sunrise: datetime, observe: frozenset) -> list[str]:
    """Season rules in force on this day, among those the goal observes."""
    if not observe:
        return []
    found = []
    positions = sidereal_positions(_jd(sunrise))
    sun = positions["Sun"]["lon"]

    def gap(planet: str) -> float:
        d = abs(positions[planet]["lon"] - sun) % 360.0
        return min(d, 360.0 - d)

    if "guru_asta" in observe and gap("Jupiter") < 11.0:
        found.append("guru_asta")
    venus_orb = 8.0 if positions["Venus"]["retrograde"] else 10.0
    if "shukra_asta" in observe and gap("Venus") < venus_orb:
        found.append("shukra_asta")
    masa = day.get("masa") or {}
    if "adhika" in observe and masa.get("adhika"):
        found.append("adhika")
    if "kharmas" in observe and sign_index(sun) in (8, 11):
        found.append("kharmas")
    if "chaturmas" in observe:
        tithi = ((day.get("elements") or {}).get("tithi") or [{}])[0].get("index", 0)
        if _in_chaturmas(masa.get("amanta") or "", masa.get("paksha") or "", tithi % 15 + 1):
            found.append("chaturmas")
    return found


# ── Blocks of a day ──────────────────────────────────────────────────────────

def _day_bounds(day: dict) -> tuple[datetime, datetime, datetime]:
    chog = day["choghadiya"]
    return (datetime.fromisoformat(chog["day"][0]["start_iso"]),
            datetime.fromisoformat(chog["day"][-1]["end_iso"]),
            datetime.fromisoformat(chog["night"][-1]["end_iso"]))


def _hours_window(day_date: date_cls, hours, tz) -> tuple[datetime, datetime] | None:
    if hours is None:
        return None
    start_h, end_h = hours
    midnight = datetime(day_date.year, day_date.month, day_date.day, tzinfo=tz)
    return midnight + timedelta(hours=start_h), midnight + timedelta(hours=end_h)


def _blocks(day: dict, goal: dict, hours) -> list[dict]:
    """The day's and night's fifteen muhurtas, each with what makes it special."""
    rise, sets, next_rise = _day_bounds(day)
    day_step = (sets - rise) / 15
    night_step = (next_rise - sets) / 15
    vara = day["vara"]["name"]
    blocks = []
    for i in range(15):
        name = None
        if i == 7 and vara != "Wednesday":
            name = "Abhijit Muhurta"
        if i == 14 and "marriage" == goal.get("lagna"):
            name = "Godhuli"
        blocks.append({"start": rise + day_step * i, "end": rise + day_step * (i + 1),
                       "name": name, "night": False})
    for i in range(15):
        blocks.append({"start": sets + night_step * i, "end": sets + night_step * (i + 1),
                       "name": "Godhuli" if i == 0 and goal.get("lagna") == "marriage" else None,
                       "night": True})
    # Brahma Muhurta of the night that ends at this sunrise (kala.py's window).
    brahma = next((w for w in day["windows"]["auspicious"] if w["name"] == "Brahma Muhurta"), None)
    if brahma and goal.get("predawn"):
        blocks.insert(0, {"start": datetime.fromisoformat(brahma["start_iso"]),
                          "end": datetime.fromisoformat(brahma["end_iso"]),
                          "name": "Brahma Muhurta", "night": True, "brahma": True})
    return blocks


def _covering(rows: list[dict], moment: datetime) -> dict | None:
    iso = moment.isoformat()
    for row in rows:
        if row["start_iso"] <= iso < row["end_iso"]:
            return row
    return None


def _overlap_share(a0: datetime, a1: datetime, b0: datetime, b1: datetime) -> float:
    inter = (min(a1, b1) - max(a0, b0)).total_seconds()
    return max(0.0, inter) / max(1.0, (a1 - a0).total_seconds())


def _plain_window_label(name: str | None, start: datetime) -> str:
    if name:
        return name
    h = start.hour
    if h < 5:
        return "Late night muhurta"
    if h < 12:
        return "Morning muhurta"
    if h < 16:
        return "Afternoon muhurta"
    if h < 20:
        return "Evening muhurta"
    return "Night muhurta"


def find(goal_slug: str, date_from: date_cls, date_to: date_cls, *,
         janma_nakshatra_index: int, janma_rashi_index: int,
         intent: str | None = None,
         ghatak_moon_sign: int | None = None,
         partner: dict | None = None,
         ceremony: str | None = None,
         direction: str | None = None,
         avoid_weekdays: list[str] | None = None,
         observe_season: bool = True,
         birth_date: date_cls | None = None,
         city: str | None = None, nation: str = "IN",
         lat: float | None = None, lng: float | None = None,
         tz_str: str | None = None,
         limit: int = 5, max_days: int = 62,
         look_ahead_days: int = 0,
         locked_from: date_cls | None = None,
         locked_days: int = 0) -> dict:
    """Find and rank good times for a purpose over a date range.

    Args:
        goal_slug: a key of :data:`GOALS`.
        intent: the reader's own words for a "general" search. Checked for
            refer-out topics, and scored by a goal's rules when it names one.
        date_from / date_to: inclusive search range. One day is the
            "I already have the date" case: the best hours on it.
        janma_nakshatra_index / janma_rashi_index: from the person's kundli.
        partner: {"nak": int, "rashi": int, "name": str} for a couple.
        ceremony: "day" or "night" for a wedding.
        direction: north/south/east/west for a journey (disha shool).
        avoid_weekdays: weekday names the family avoids for this.
        observe_season: apply the goal's season rules (Chaturmas and so on).
        birth_date: the person's birth date, for the customary age of
            child ceremonies.
        city/nation or lat/lng/tz_str: where it will happen.
        limit: how many slots to return.
        max_days: guard against unbounded ranges.
        look_ahead_days: when the range has fewer than three good slots, look
            this many days past it for the next good date.
        locked_from / locked_days: for a plan with a horizon, the first good
            date from ``locked_from`` on, returned as ``locked_next`` with
            the date and quality only. The time stays with the plan that
            can see it.

    Raises:
        ExcludedGoalError: for health/legal/financial intents.
        ValueError: for an unknown goal or an inverted/oversized range.
    """
    domain = _excluded_domain(goal_slug, whole_words=False)
    if domain is None and intent:
        domain = _excluded_domain(intent, whole_words=True)
    if domain:
        raise ExcludedGoalError(domain)

    if goal_slug not in GOALS:
        raise ValueError(f"Unknown goal '{goal_slug}'. Known: {sorted(GOALS)}")
    rules_slug = goal_slug
    if goal_slug == "general" and intent:
        rules_slug = goal_for_intent(intent) or goal_slug
    goal = GOALS[rules_slug]
    if date_to < date_from:
        raise ValueError("date_to must not be before date_from")
    span = (date_to - date_from).days + 1
    if span > max_days:
        raise ValueError(f"Range too large ({span} days); max is {max_days}")

    hours, hours_note = goal.get("hours"), goal.get("hours_note")
    if goal.get("lagna") == "marriage" and ceremony in CEREMONY_HOURS:
        hours, hours_note = CEREMONY_HOURS[ceremony]
    avoid = {w.capitalize() for w in (avoid_weekdays or [])} | set(goal.get("avoid_vara") or [])
    direction = (direction or "").lower() or None
    if direction not in _DIRECTIONS:
        direction = None
    observe = goal.get("season", frozenset()) if observe_season else frozenset()
    lat, lng, tz_str = resolve_location(city, nation, lat, lng, tz_str)
    me = {"nak": janma_nakshatra_index, "rashi": janma_rashi_index}

    scan = _scan(goal, rules_slug, date_from, span, me, partner, ghatak_moon_sign,
                 hours, avoid, direction, observe, lat, lng, tz_str, city, nation)
    results, more = _select(scan["candidates"], limit)

    next_good = None
    good_count = sum(1 for c in scan["candidates"] if c["score"] >= _GOOD_SCORE)
    if look_ahead_days > 0 and good_count < 3:
        ahead = _scan(goal, rules_slug, date_to + timedelta(days=1),
                      min(look_ahead_days, max_days), me, partner, ghatak_moon_sign,
                      hours, avoid, direction, observe, lat, lng, tz_str, city, nation)
        good = sorted((c for c in ahead["candidates"] if c["score"] >= _GOOD_SCORE),
                      key=lambda c: c["start_iso"])
        if good:
            next_good = {k: good[0][k] for k in ("date", "start", "end", "score", "quality", "label")}

    locked_next = None
    # Two weeks at a time: the first good date is usually in the first.
    for offset in range(0, locked_days if locked_from else 0, 14):
        ahead = _scan(goal, rules_slug, locked_from + timedelta(days=offset),
                      min(14, locked_days - offset), me, partner, ghatak_moon_sign,
                      hours, avoid, direction, observe, lat, lng, tz_str, city, nation)
        good = sorted((c for c in ahead["candidates"] if c["score"] >= _GOOD_SCORE),
                      key=lambda c: c["start_iso"])
        if good:
            locked_next = {"date": good[0]["date"], "quality": good[0]["quality"]}
            break

    notes = []
    if not results:
        notes.append("No time in these dates clears the bar. Widening the dates "
                     "usually helps more than settling for a weak slot.")
    if scan["out_of_hours"] and hours_note:
        notes.append(hours_note)
    for code, days in scan["season_days"].items():
        notes.append(f"{len(days)} day{'s' if len(days) != 1 else ''} left out "
                     f"{SEASON_TEXT[code][1]}, as many families wait then. You can "
                     "turn this off if yours does not.")
    if scan["chandrashtama_days"]:
        n = len(scan["chandrashtama_days"])
        notes.append(f"{n} day{'s' if n != 1 else ''} left out when the Moon is in a hard "
                     "place for " + ("one of you" if partner else "you") + " (Chandrashtama).")
    if scan["avoided_days"]:
        notes.append(f"{len(scan['avoided_days'])} day(s) left out for "
                     f"{', '.join(sorted(avoid))}, as you asked.")
    if scan["shool_days"]:
        notes.append(f"{len(scan['shool_days'])} day(s) left out because travelling "
                     f"{direction} on that weekday is traditionally avoided (disha shool).")
    samskara = _samskara_note(rules_slug, birth_date, date_from)
    if samskara:
        notes.append(samskara)

    return {
        "goal": goal_slug,
        "goal_label": GOALS[goal_slug]["label"],
        "rules_goal": rules_slug,
        "rules_label": goal["label"],
        "whose": goal.get("whose", "self"),
        "date_from": date_from.isoformat(),
        "date_to": date_to.isoformat(),
        "days_scanned": scan["days_scanned"],
        "skipped_days": scan["skipped"],
        "results": results,
        "count": len(results),
        "more_available": more,
        "next_good": next_good,
        "locked_next": locked_next,
        "notes": notes,
        "note": " ".join(notes) or None,
        "hours": list(hours) if hours else None,
        "season_rules": sorted(observe),
        "is_convention_dependent": True,
        "observance_note": OBSERVANCE_NOTE,
        "rules_source": goal.get("source"),
        "disclaimer": (
            "Timing supports your intent; the decision and the care are still "
            "yours. Muhurta is not offered for health, legal or financial "
            "matters; please consult a qualified professional for those."
        ),
    }


def _scan(goal, rules_slug, date_from, span, me, partner, ghatak_moon_sign,
          hours, avoid, direction, observe, lat, lng, tz_str, city, nation) -> dict:
    candidates: list[dict] = []
    skipped: list[dict] = []
    season_days: dict[str, list[str]] = {}
    chandrashtama_days, avoided_days, shool_days = [], [], []
    out_of_hours = 0
    days_scanned = 0
    festival_dates = _festival_dates(goal, date_from, span, lat, lng, tz_str)

    for offset in range(span):
        day_date = date_from + timedelta(days=offset)
        vara = VARA_NAMES[(day_date.weekday() + 1) % 7]
        if vara in avoid:
            avoided_days.append(day_date.isoformat())
            continue
        if goal.get("travel") and direction and DISHA_SHOOL.get(vara, "").lower() == direction:
            shool_days.append(day_date.isoformat())
            continue
        try:
            day = daily_panchanga(day_date.year, day_date.month, day_date.day,
                                  city=city, nation=nation, lat=lat, lng=lng, tz_str=tz_str)
        except ValueError as exc:  # circumpolar / undefined sunrise
            skipped.append({"date": day_date.isoformat(), "reason": str(exc)})
            continue
        days_scanned += 1
        rise, _sets, _next = _day_bounds(day)
        blocked = _season_blocks(day, rise, observe)
        if blocked:
            for code in blocked:
                season_days.setdefault(code, []).append(day_date.isoformat())
            continue

        personal = personal_panchanga(day, me["nak"], me["rashi"], ghatak_moon_sign)
        ghatak = [a["type"] for a in (personal.get("ghatak_alerts") or []) if a.get("matched")]
        inauspicious = day["windows"]["inauspicious"]
        amrit = [w for w in day["windows"]["auspicious"] if w["name"].startswith("Amrit Kalam")]
        window = _hours_window(day_date, hours, rise.tzinfo)
        festival = festival_dates.get(day_date)
        day_chandrashtama = False

        for block in _blocks(day, goal, hours):
            b_start, b_end = block["start"], block["end"]
            if window:
                if b_end <= window[0] or b_start >= window[1]:
                    if not block.get("brahma"):
                        out_of_hours += 1
                        continue
                elif not block.get("brahma"):
                    b_start, b_end = max(b_start, window[0]), min(b_end, window[1])
            if b_end - b_start < timedelta(minutes=_MIN_USABLE_MINUTES):
                out_of_hours += 1
                continue
            raw = {"start_iso": b_start.isoformat(), "end_iso": b_end.isoformat()}
            clear = _clear_span(raw, inauspicious)
            if clear is None:
                continue
            c_start, c_end = clear
            trimmed = (c_start, c_end) != (b_start, b_end)
            clashes = sorted({bad["name"] for bad in inauspicious
                              if _overlaps(raw["start_iso"], raw["end_iso"],
                                           bad["start_iso"], bad["end_iso"])})

            scored = _score_block(goal, day, vara, block, c_start, c_end, me, partner,
                                  amrit, festival, ghatak, lat, lng)
            if scored is None:
                day_chandrashtama = True
                continue
            points, plus, minus, terms, name, badges, facts = scored
            if trimmed:
                points -= 4
                cut = ", ".join(clashes)
                minus.append(f"Shortened to keep clear of {cut}")
                terms.append(f"Trimmed to avoid {cut}")
            else:
                plus.append("Clear of Rahu Kalam and the other times to avoid")

            score = max(0, min(100, round(points * 100 / _FULL_MARKS)))
            if score < _MIN_SCORE:
                continue
            quality = ("best" if score >= _BEST_SCORE
                       else "good" if score >= _GOOD_SCORE else "workable")
            candidates.append({
                "date": day_date.isoformat(),
                "window": _plain_window_label(name, c_start),
                "start": c_start.strftime("%H:%M"),
                "end": c_end.strftime("%H:%M"),
                "start_iso": c_start.isoformat(),
                "end_iso": c_end.isoformat(),
                "trimmed": trimmed,
                "night": _is_night(c_start, c_end),
                "weekend": vara in ("Saturday", "Sunday"),
                "duration_minutes": int((c_end - c_start).total_seconds() // 60),
                "score": score,
                "quality": quality,
                "label": QUALITY_WORDS[quality],
                "badges": badges,
                "why": {"supports": plus, "against": minus, "terms": terms},
                "vara": vara,
                "nakshatra": facts["nakshatra"],
                "tithi": facts["tithi"],
            })
        if day_chandrashtama:
            chandrashtama_days.append(day_date.isoformat())

    return {"candidates": _merge(candidates), "skipped": skipped,
            "season_days": season_days, "chandrashtama_days": chandrashtama_days,
            "avoided_days": avoided_days, "shool_days": shool_days,
            "out_of_hours": out_of_hours, "days_scanned": days_scanned}


def _score_block(goal, day, vara, block, start, end, me, partner, amrit, festival,
                 ghatak, lat, lng):
    """Points for one block. None when the block is ruled out for the person."""
    mid = start + (end - start) / 2
    facts = _moment_facts(mid)
    plus: list[str] = []
    minus: list[str] = []
    terms: list[str] = []
    badges: list[str] = []
    points = _BLOCK_BASE
    name = block.get("name")

    if name == "Abhijit Muhurta":
        points += 14
        plus.append("Midday Abhijit, a strong time for most work")
        terms.append("Abhijit Muhurta")
    elif name == "Brahma Muhurta":
        points += 10 if goal.get("predawn") else 4
        plus.append("Brahma Muhurta, the calm hour before dawn")
        terms.append("Brahma Muhurta")
    elif name == "Godhuli":
        points += 8
        plus.append("Godhuli, the dusk hour held good for weddings")
        terms.append("Godhuli lagna")

    if any(_overlap_share(start, end, datetime.fromisoformat(a["start_iso"]),
                          datetime.fromisoformat(a["end_iso"])) >= 0.5 for a in amrit):
        points += 10
        plus.append("Inside Amrit Kalam, a nectar-like stretch of the day")
        terms.append("Amrit Kalam")
        if not name:
            name = "Amrit Kalam"

    chog_rows = day["choghadiya"]["night" if block.get("night") else "day"]
    chog = _covering(chog_rows, mid) or _covering(day["choghadiya"]["day"] + day["choghadiya"]["night"], mid)
    if chog:
        pts = _CHOGHADIYA_POINTS.get(chog["name"], 0)
        points += pts
        if pts > 0:
            plus.append(f"{chog['name']} choghadiya, a good part of the day")
            if not name:
                name = f"{chog['name']} Choghadiya"
        elif pts < 0:
            minus.append(f"{chog['name']} choghadiya, a weaker part of the day")
        terms.append(f"Choghadiya: {chog['name']}")

    hora = _covering(day.get("horas") or [], mid)
    if hora and goal.get("hora") and hora["name"].startswith(goal["hora"]):
        points += 4
        plus.append(f"In the hour of {goal['hora']}, which suits this")
        terms.append(hora["name"])

    lagna_rule = goal.get("lagna")
    if lagna_rule:
        jd = _jd(mid)
        lagna = sign_index(sidereal_lagna(jd, lat, lng))
        terms.append(f"Lagna: {sign_name(lagna)}")
        if lagna_rule == "marriage":
            positions = sidereal_positions(jd)
            bad = [p for p in _MALEFICS
                   if (sign_index(positions[p]["lon"]) - lagna) % 12 + 1 in (7, 8)]
            if bad:
                points -= 8
                minus.append("A hard planet sits in the marriage houses of this rising sign")
                terms.append(f"7th/8th from lagna: {', '.join(bad)}")
            else:
                points += 6
                plus.append("The rising sign has its marriage houses clear")
                terms.append("Lagna shuddhi: 7th and 8th clear of malefics")
        else:
            signs, why = _LAGNA_TYPES[lagna_rule]
            if lagna in goal.get("avoid_lagna", {}):
                points -= 6
                minus.append(goal["avoid_lagna"][lagna])
            elif lagna in signs:
                points += 6
                plus.append(f"Rising sign is {why}")

    if goal["prefer_vara"] and vara in goal["prefer_vara"]:
        points += 10
        plus.append(f"{vara} suits this")
    elif vara in goal.get("shun_vara", ()):
        points -= 8
        minus.append(f"{vara} is a day the old rules avoid for this")
    terms.append(f"Vara: {vara}")
    if goal["prefer_nakshatra"] and facts["nakshatra"] in goal["prefer_nakshatra"]:
        points += 12
        plus.append(f"A favourable star for this ({facts['nakshatra']})")
    terms.append(f"Nakshatra: {facts['nakshatra']}")
    if facts["tithi_number"] in goal["avoid_tithi"] or (
            facts["tithi_index"] == 29 and goal["avoid_tithi"]):
        points -= 14
        minus.append(f"The lunar day ({facts['tithi']}) is one people usually avoid for this")
    if goal.get("shukla") and facts["paksha"] == "Shukla":
        points += 4
        plus.append("The waxing half of the month, preferred for this")
    terms.append(f"Tithi: {facts['tithi']}")
    if facts["yoga"] in _BAD_YOGAS:
        points -= 10
        minus.append(f"The day's yoga ({facts['yoga']}) is avoided for new starts")
    terms.append(f"Yoga: {facts['yoga']}")
    if goal.get("panchaka") and facts["nakshatra_index"] in PANCHAKA_NAKSHATRA_IDX:
        points -= 10
        minus.append("Panchaka is running, which many families avoid for this")
        terms.append("Panchaka")

    for special in _special_days(vara, facts):
        badges.append(special)
        if special in ("Guru Pushya", "Ravi Pushya"):
            lift = 10 if goal.get("special") else 4
        elif special == "Amrit Siddhi":
            lift = 6
        elif special == "Sarvartha Siddhi":
            lift = 4
        else:  # Pushkar yogas multiply what is begun: good for buying only
            lift = 6 if goal.get("special") else 0
        if lift:
            points += lift
            plus.append(f"{special} day, sought after for this")
        terms.append(f"Special day: {special}")
    if festival:
        badges.append(FESTIVAL_NAMES.get(festival, festival))
        points += 8
        plus.append(f"{FESTIVAL_NAMES.get(festival, festival)}, a traditional day for this")

    pts, chandrashtama = _person_factors(facts, me, "you", plus, minus, terms)
    points += pts
    if partner:
        p_pts, p_chandrashtama = _person_factors(
            facts, partner, partner.get("name") or "your partner", plus, minus, terms)
        points += p_pts
        chandrashtama = chandrashtama or p_chandrashtama
    if chandrashtama and goal.get("major"):
        return None
    if ghatak:
        points -= 6
        minus.append("One of your personal caution days")
        terms.append(f"Ghatak: {', '.join(ghatak)}")

    return points, plus, minus, terms, name, badges, facts


def _merge(candidates: list[dict]) -> list[dict]:
    """Join back-to-back blocks of the same standing into one slot."""
    candidates.sort(key=lambda c: c["start_iso"])
    merged: list[dict] = []
    run = 1
    for c in candidates:
        last = merged[-1] if merged else None
        if (last and last["date"] == c["date"] and last["end_iso"] == c["start_iso"]
                and last["quality"] == c["quality"] and run < _MAX_MERGE_BLOCKS
                and not last["trimmed"] and not c["trimmed"]):
            keep = last if last["score"] >= c["score"] else c
            joined = dict(keep)
            joined["start"], joined["start_iso"] = last["start"], last["start_iso"]
            joined["end"], joined["end_iso"] = c["end"], c["end_iso"]
            joined["duration_minutes"] = last["duration_minutes"] + c["duration_minutes"]
            joined["night"] = last["night"] or c["night"]
            joined["badges"] = sorted(set(last["badges"]) | set(c["badges"]))
            merged[-1] = joined
            run += 1
        else:
            merged.append(dict(c))
            run = 1
    return merged


def _select(candidates: list[dict], limit: int) -> tuple[list[dict], int]:
    """Best first, at most two a day, and a weekend slot when one qualifies."""
    ranked = sorted(candidates, key=lambda c: (-c["score"], c["start_iso"]))
    picked: list[dict] = []
    per_day: dict[str, int] = {}
    for c in ranked:
        if per_day.get(c["date"], 0) >= _MAX_PER_DAY:
            continue
        if any(p["date"] == c["date"] and _overlaps(p["start_iso"], p["end_iso"],
                                                    c["start_iso"], c["end_iso"])
               for p in picked):
            continue
        picked.append(c)
        per_day[c["date"]] = per_day.get(c["date"], 0) + 1
    results = picked[:limit]
    if results and not any(r["weekend"] for r in results):
        weekend = next((c for c in picked[limit:] if c["weekend"] and c["score"] >= _GOOD_SCORE), None)
        if weekend:
            results[-1] = weekend
            results.sort(key=lambda c: (-c["score"], c["start_iso"]))
    return results, max(0, len(picked) - len(results))


def _festival_dates(goal, date_from, span, lat, lng, tz_str) -> dict:
    slugs = goal.get("festivals")
    if not slugs:
        return {}
    from . import festivals  # local: the festival engine is heavy to import
    end = date_from + timedelta(days=span - 1)
    out = {}
    for year in sorted({date_from.year, end.year}):
        try:
            rows = festivals.occurrences(year, lat=lat, lng=lng, tz_str=tz_str, slugs=slugs)
        except Exception:  # festival rules are a bonus, never a failure
            continue
        for row in rows:
            if date_from <= row["occurs_on"] <= end:
                out[row["occurs_on"]] = row["slug"]
    return out


def _samskara_note(slug: str, birth_date: date_cls | None, today: date_cls) -> str | None:
    """The customary age for a child's ceremony, from the child's birth date."""
    if not birth_date:
        return None
    if slug == "namakarana":
        days = [birth_date + timedelta(days=n) for n in (10, 11, 15, 21)]
        upcoming = [d for d in days if d >= today]
        if upcoming:
            return ("Naming is traditionally done on the 11th, 12th, 16th or 22nd day "
                    "after birth: " + ", ".join(d.strftime("%-d %b") for d in upcoming) + ".")
        return None
    if slug == "annaprashana":
        start = birth_date + timedelta(days=150)
        end = birth_date + timedelta(days=240)
        return (f"The first meal is usually given in the 6th month for a boy, or the 5th "
                f"or 7th for a girl: about {start.strftime('%-d %b')} to "
                f"{end.strftime('%-d %b %Y')} for this child.")
    if slug == "mundan":
        age = (today - birth_date).days // 365
        odd = age + 1 if (age + 1) % 2 == 1 else age + 2
        return (f"Mundan is traditionally done in an odd year of age (1st, 3rd or 5th). "
                f"This child is in year {age + 1}; the next odd year is year {odd}.")
    return None


def goal_catalog() -> list[dict]:
    """Goals in a shape that maps onto the ``muhurta_goals`` table."""
    return [
        {
            "slug": slug,
            "label": spec["label"],
            "description": spec.get("hours_note"),
            "rules": {
                "category": spec.get("category"),
                "prefer_vara": spec["prefer_vara"],
                "prefer_nakshatra": spec["prefer_nakshatra"],
                "avoid_tithi": sorted(spec["avoid_tithi"]),
                "hours": list(spec["hours"]) if spec.get("hours") else None,
                "season": sorted(spec.get("season", ())),
                "whose": spec.get("whose", "self"),
            },
            "is_active": True,
        }
        for slug, spec in GOALS.items()
    ]
