"""Hindu festival calendar — computes observance dates from panchanga.

Covers the major North Indian and South Indian festivals. Dates are derived,
never hardcoded: each festival carries a rule, and :func:`occurrences` walks a
year's panchanga to resolve it for a given place.

Why place matters
-----------------
A tithi is a Moon-Sun elongation, not a day. The observed day is the one where
the required tithi is current **at sunrise**, so the answer genuinely depends
on longitude — Diwali can differ by a day between Chennai and New Jersey.
Every result therefore records the place it was computed for.

Amanta vs Purnimanta
--------------------
The single biggest source of error in festival tables. The South (and Gujarat)
ends the lunar month at the new moon (**amanta**); the North ends it at the
full moon (**purnimanta**). The two systems agree on Shukla-paksha dates but
name Krishna-paksha months differently — Krishna paksha belongs to the *next*
month under purnimanta reckoning.

So Maha Shivaratri is *Phalguna* Krishna Chaturdashi in the North and *Magha*
Krishna Chaturdashi in the South — the same day, two names. Rather than
converting between them (error-prone), each rule declares which reckoning its
month name is stated in, and matching compares against the corresponding field
that :func:`~astrospace.core.vedic.masa.amanta_masa` already returns.

Determining moments
-------------------
"Tithi prevailing at sunrise" is the default, but it is not universal, and
using it everywhere puts real festivals on the wrong day:

* **nishita** (midnight) — Maha Shivaratri. Chaturdashi begins after sunrise,
  so the sunrise rule lands a day late.
* **pradosh** (evening) — Lakshmi Puja on Diwali. Amavasya arrives during the
  day, so the sunrise rule again lands a day late.
* **sunset rule** for Sankrantis — the solar month begins on the ingress day
  when the crossing precedes sunset. Taking the next sunrise unconditionally
  puts Pongal and Puthandu a day late.

Two panchanga edge cases are handled explicitly rather than silently dropping
or duplicating a festival:

* **kshaya tithi** — a tithi shorter than a day can be current at no sunrise
  at all (Chaitra Shukla Pratipada does this in 2026, which would lose Ugadi).
  The observance falls on the day the tithi begins.
* **adhika masa** — in an intercalary year a month name occurs twice.
  Festivals are placed in the nija (true) month, and the occurrence says so.

What is still convention-dependent
----------------------------------
Moonrise-determined fasts (Karva Chauth, Atla Taddi), Ekadashi variants
between Smarta and Vaishnava usage, and Upakarma across Veda shakhas cannot be
reduced to one date. Those carry ``observance_note`` and
``is_convention_dependent`` so the caller can surface the caveat rather than
implying false precision. Regional almanacs (panchangam/panjika) remain the
authority for ritual timing.
"""
from __future__ import annotations

from datetime import date as date_cls, timedelta

from .constants import LUNAR_MONTHS, NAKSHATRAS
from .masa import amanta_masa
from .nakshatra import nakshatra_of
from .panchanga import tithi_of
from .positions import day_span, resolve_location, sidereal_positions, sign_index

# Tithi numbers are 1..15 within a paksha. These aliases make rules readable.
PURNIMA = 15
AMAVASYA = 15  # the 15th tithi of Krishna paksha

# Region tags
NORTH, SOUTH, PAN = "north", "south", "pan-india"


def _f(slug, name, rule, *, regions, local_names=None, description=None,
       prep=None, observance_note=None, convention_dependent=False):
    return {
        "slug": slug,
        "name": name,
        "local_names": local_names or {},
        "regions": regions,
        "description": description,
        "prep_guidance": prep,
        "rule": rule,
        "observance_note": observance_note,
        "is_convention_dependent": convention_dependent,
    }


def _lunar(month, paksha, tithi, reckoning="amanta", at="sunrise"):
    """Tithi-based rule.

    ``reckoning`` says which system ``month`` is named in. ``at`` is the moment
    the tithi must be current: most festivals use ``"sunrise"``, but some are
    fixed by ``"pradosh"`` (evening, e.g. Lakshmi Puja on Diwali) or
    ``"nishita"`` (midnight, e.g. Maha Shivaratri) — using sunrise for those
    lands a day early or late.
    """
    return {"type": "lunar_tithi", "month": month, "paksha": paksha,
            "tithi": tithi, "reckoning": reckoning, "at": at}


def _solar(sign, offset=0):
    """Sankranti rule — the day the Sun enters the given sidereal sign.

    ``offset`` shifts by whole days from the month's first day, for festivals
    defined relative to it: Bhogi and Lohri fall on ``-1``, Aadi Perukku on the
    18th of Aadi (``+17``).
    """
    return {"type": "solar_sankranti", "sign": sign, "offset": offset}


def _nak_in_solar(nakshatra, sign, which="first"):
    """Nakshatra-in-solar-month rule (Onam, Karthigai Deepam…).

    ``which`` picks the occurrence when the nakshatra recurs inside a single
    solar month. That is not hypothetical: Karka (Aadi) runs about 31.4 days
    against the nakshatra's 27.3, so Pooram can fall twice in one Aadi.
    """
    return {"type": "nakshatra_in_solar_month", "nakshatra": nakshatra,
            "sign": sign, "which": which}


def _weekday_before(month, paksha, tithi, weekday, reckoning="amanta"):
    """Last given weekday on or before a tithi (Varalakshmi Vratam)."""
    return {"type": "weekday_before_tithi", "month": month, "paksha": paksha,
            "tithi": tithi, "weekday": weekday, "reckoning": reckoning}


# ── Catalog ──────────────────────────────────────────────────────────────────
# Ordered roughly by the lunar year (Chaitra → Phalguna), with solar festivals
# placed where they fall.

# Recurring caveats, shared so the wording stays identical wherever it applies.
_EKADASHI_NOTE = ("Ekadashi dates vary between Smarta and Vaishnava usage; "
                  "Vaishnavas may observe a day later.")
_MOONRISE_NOTE = "Determined by moonrise, which varies by city."

FESTIVALS: list[dict] = [
    # ── Chaitra ──────────────────────────────────────────────────────────────
    _f("ugadi", "Ugadi / Gudi Padwa", _lunar("Chaitra", "Shukla", 1),
       regions=[SOUTH, NORTH],
       local_names={"te": "ఉగాది", "ta": "யுகாதி", "mr": "गुढी पाडवा"},
       description="Lunar new year in the Deccan and Maharashtra.",
       prep="Prepare Ugadi pachadi; clean and decorate the doorway."),
    _f("gauri_habba", "Gauri Habba / Cheti Chand", _lunar("Chaitra", "Shukla", 3),
       regions=[SOUTH],
       description="Gauri worship in Karnataka; Cheti Chand for Sindhis."),
    _f("rama_navami", "Rama Navami", _lunar("Chaitra", "Shukla", 9),
       regions=[PAN],
       local_names={"te": "శ్రీరామ నవమి", "ta": "ராம நவமி"},
       description="Birth of Rama.",
       prep="Panakam and vada pappu are offered in the Telugu tradition."),
    _f("hanuman_jayanti", "Hanuman Jayanti", _lunar("Chaitra", "Shukla", PURNIMA),
       regions=[NORTH],
       description="Birth of Hanuman (North Indian reckoning).",
       observance_note="Tamil Nadu observes Hanumath Jayanti in Margazhi instead.",
       convention_dependent=True),

    # ── Solar new years (Mesha Sankranti) ────────────────────────────────────
    _f("tamil_puthandu", "Puthandu / Vishu / Baisakhi", _solar(0),
       regions=[SOUTH, NORTH],
       local_names={"ta": "புத்தாண்டu", "ml": "വിഷു", "pa": "ਵਿਸਾਖੀ"},
       description="Solar new year — Tamil Puthandu, Kerala Vishu, Punjab Baisakhi.",
       prep="Vishukkani is arranged the night before, seen first on waking."),

    # ── Vaishakha ────────────────────────────────────────────────────────────
    _f("akshaya_tritiya", "Akshaya Tritiya", _lunar("Vaishakha", "Shukla", 3),
       regions=[PAN],
       description="Considered auspicious for beginnings and for buying gold.",
       prep="Traditionally a day for charity as much as for purchase."),
    _f("narasimha_jayanti", "Narasimha Jayanti", _lunar("Vaishakha", "Shukla", 14),
       regions=[PAN], description="Appearance of Narasimha."),
    _f("buddha_purnima", "Buddha Purnima / Vaishakha Purnima",
       _lunar("Vaishakha", "Shukla", PURNIMA), regions=[PAN],
       description="Birth of the Buddha; also Kurma Jayanti."),

    # ── Jyeshtha ─────────────────────────────────────────────────────────────
    _f("vat_savitri", "Vat Savitri Vrat",
       _lunar("Jyeshtha", "Krishna", AMAVASYA, reckoning="purnimanta"),
       regions=[NORTH],
       description="Observed by married women for the wellbeing of their husband.",
       observance_note="Amavasya in the North; some regions observe on Purnima.",
       convention_dependent=True),
    _f("ganga_dussehra", "Ganga Dussehra", _lunar("Jyeshtha", "Shukla", 10),
       regions=[NORTH], description="Descent of the Ganga."),

    # ── Ashadha ──────────────────────────────────────────────────────────────
    _f("rath_yatra", "Rath Yatra", _lunar("Ashadha", "Shukla", 2),
       regions=[PAN], description="Jagannath Rath Yatra, Puri."),
    _f("guru_purnima", "Guru Purnima", _lunar("Ashadha", "Shukla", PURNIMA),
       regions=[PAN], description="Honouring one's teachers."),

    # ── Shravana ─────────────────────────────────────────────────────────────
    _f("nag_panchami", "Nag Panchami", _lunar("Shravana", "Shukla", 5),
       regions=[PAN],
       local_names={"te": "నాగ పంచమి"},
       description="Reverence for serpent deities.",
       prep="Temple visit at sunrise; offerings of milk."),
    _f("varalakshmi_vratam", "Varalakshmi Vratam",
       _weekday_before("Shravana", "Shukla", PURNIMA, weekday=4),
       regions=[SOUTH],
       local_names={"te": "వరలక్ష్మీ వ్రతం", "ta": "வரலட்சுமி விரதம்"},
       description="Lakshmi vrat observed by married women in the Telugu and Tamil south.",
       prep="Begin preparations two days ahead; kalasham is set on the eve.",
       observance_note="The Friday on or before Shravana Purnima."),
    _f("raksha_bandhan", "Raksha Bandhan", _lunar("Shravana", "Shukla", PURNIMA),
       regions=[NORTH],
       description="Sisters tie a rakhi; also Avani Avittam / Upakarma in the south.",
       observance_note="Bhadra must be avoided for tying the rakhi.",
       convention_dependent=True),
    _f("krishna_janmashtami", "Krishna Janmashtami",
       _lunar("Shravana", "Krishna", 8),
       regions=[PAN],
       local_names={"te": "శ్రీ కృష్ణ జన్మాష్టమి", "ta": "கோகுலாஷ்டமி"},
       description="Birth of Krishna. Bhadrapada Krishna Ashtami in purnimanta reckoning.",
       observance_note="Fixed by midnight (nishita), not sunrise; smarta and "
                       "vaishnava observances can fall on different days.",
       convention_dependent=True),

    # ── Bhadrapada ───────────────────────────────────────────────────────────
    _f("ganesh_chaturthi", "Ganesh Chaturthi / Vinayaka Chavithi",
       _lunar("Bhadrapada", "Shukla", 4), regions=[PAN],
       local_names={"te": "వినాయక చవితి", "mr": "गणेश चतुर्थी"},
       description="Installation and worship of Ganesha.",
       prep="Clay idol, patri (21 leaves), and undrallu/modak."),
    _f("onam", "Onam (Thiruvonam)", _nak_in_solar("Shravana", 4),
       regions=[SOUTH], local_names={"ml": "ഓണം"},
       description="Kerala harvest festival, on Thiruvonam nakshatra in Chingam.",
       prep="Pookalam from Atham; Onasadya on Thiruvonam."),
    _f("mahalaya_amavasya", "Mahalaya Amavasya",
       _lunar("Bhadrapada", "Krishna", AMAVASYA), regions=[PAN],
       description="Close of Pitru Paksha; tarpanam for ancestors."),

    # ── Ashwina ──────────────────────────────────────────────────────────────
    _f("navratri_begins", "Sharada Navratri begins",
       _lunar("Ashwina", "Shukla", 1), regions=[PAN],
       description="Nine nights of Durga; Bathukamma begins in Telangana."),
    _f("durga_ashtami", "Durga Ashtami", _lunar("Ashwina", "Shukla", 8),
       regions=[PAN], description="Mahashtami — the eighth night of Navratri."),
    _f("ayudha_puja", "Ayudha Puja / Maha Navami",
       _lunar("Ashwina", "Shukla", 9), regions=[SOUTH],
       local_names={"ta": "ஆயுத பூஜை", "te": "ఆయుధ పూజ"},
       description="Tools, instruments and vehicles are honoured."),
    _f("vijayadashami", "Vijayadashami / Dussehra",
       _lunar("Ashwina", "Shukla", 10), regions=[PAN],
       local_names={"te": "విజయదశమి", "ta": "விஜயதசமி"},
       description="Victory of good over evil; an auspicious day to begin learning."),
    _f("sharad_purnima", "Sharad Purnima", _lunar("Ashwina", "Shukla", PURNIMA),
       regions=[NORTH], description="Kojagari Purnima."),
    _f("karva_chauth", "Karva Chauth", _lunar("Kartika", "Krishna", 4,
                                              reckoning="purnimanta"),
       regions=[NORTH],
       description="Fast observed by married women, broken at moonrise.",
       observance_note=_MOONRISE_NOTE,
       convention_dependent=True),

    # ── Kartika (Diwali cluster) ─────────────────────────────────────────────
    _f("dhanteras", "Dhanteras", _lunar("Kartika", "Krishna", 13,
                                        reckoning="purnimanta"),
       regions=[PAN], description="Dhanvantari Trayodashi; start of the Diwali sequence.",
       observance_note="Trayodashi is the 13th tithi.",
       convention_dependent=True),
    _f("naraka_chaturdashi", "Naraka Chaturdashi / Choti Diwali",
       _lunar("Kartika", "Krishna", 14, reckoning="purnimanta"),
       regions=[PAN], local_names={"te": "నరక చతుర్దశి"},
       description="Abhyanga snanam before dawn in the south."),
    _f("diwali", "Diwali / Deepavali", _lunar("Kartika", "Krishna", AMAVASYA,
                                              reckoning="purnimanta", at="pradosh"),
       regions=[PAN],
       local_names={"te": "దీపావళి", "ta": "தீபாவளி", "hi": "दीवाली"},
       description="Festival of lights; Lakshmi Puja in the evening.",
       prep="Clean and light the home; lamps at dusk.",
       observance_note="Lakshmi Puja needs Amavasya during pradosh (evening).",
       convention_dependent=True),
    _f("govardhan_puja", "Govardhan Puja / Bali Pratipada",
       _lunar("Kartika", "Shukla", 1), regions=[NORTH],
       description="Annakut offering."),
    _f("bhai_dooj", "Bhai Dooj / Yama Dwitiya", _lunar("Kartika", "Shukla", 2),
       regions=[NORTH], description="Sisters honour their brothers."),
    _f("chhath", "Chhath Puja", _lunar("Kartika", "Shukla", 6),
       regions=[NORTH],
       description="Sun worship of Bihar, Jharkhand and eastern UP.",
       prep="Nahay Khay and Kharna precede the main day.",
       observance_note="Observed over four days; the sixth tithi is the main evening arghya."),
    _f("tulsi_vivah", "Tulsi Vivah", _lunar("Kartika", "Shukla", 12),
       regions=[PAN], description="Ceremonial marriage of Tulsi.",
       observance_note="Observed on Ekadashi or Dwadashi depending on tradition.",
       convention_dependent=True),
    _f("kartika_purnima", "Kartika Purnima / Dev Deepawali",
       _lunar("Kartika", "Shukla", PURNIMA), regions=[PAN],
       description="Lamps on the ghats; also Guru Nanak Jayanti."),
    _f("karthigai_deepam", "Karthigai Deepam", _nak_in_solar("Krittika", 7),
       regions=[SOUTH], local_names={"ta": "கார்த்திகை தீபம்"},
       description="Tamil festival of lights on Krittika nakshatra in Kartikai."),

    # ── Margashirsha / Pausha ────────────────────────────────────────────────
    _f("gita_jayanti", "Gita Jayanti / Mokshada Ekadashi",
       _lunar("Margashirsha", "Shukla", 11), regions=[PAN],
       description="Commemorates the Bhagavad Gita."),
    _f("vaikuntha_ekadashi", "Vaikuntha Ekadashi",
       _lunar("Margashirsha", "Shukla", 11), regions=[SOUTH],
       local_names={"ta": "வைகுண்ட ஏகாதசி", "te": "వైకుంఠ ఏకాదశి"},
       description="Ekadashi of the Dhanurmasa; the Vaikuntha Dwaram is opened.",
       observance_note="Falls in Dhanurmasa; some panchangams place it in Pausha.",
       convention_dependent=True),

    # ── Makara Sankranti cluster (solar) ─────────────────────────────────────
    _f("makar_sankranti", "Makar Sankranti / Pongal", _solar(9),
       regions=[PAN],
       local_names={"ta": "தைப் பொங்கல்", "te": "సంక్రాంతి", "gu": "ઉત્તરાયણ"},
       description="Sun enters Capricorn; Thai Pongal in Tamil Nadu, "
                   "Sankranti in the Telugu states, Uttarayan in Gujarat.",
       prep="Pongal is cooked at sunrise; Bhogi bonfire the day before."),

    # ── Magha ────────────────────────────────────────────────────────────────
    _f("vasant_panchami", "Vasant Panchami / Saraswati Puja",
       _lunar("Magha", "Shukla", 5), regions=[PAN],
       description="Saraswati worship; an auspicious day to begin learning."),
    _f("ratha_saptami", "Ratha Saptami", _lunar("Magha", "Shukla", 7),
       regions=[SOUTH], local_names={"te": "రథ సప్తమి"},
       description="Surya's chariot turns north."),
    _f("thai_poosam", "Thaipusam", _nak_in_solar("Pushya", 9),
       regions=[SOUTH], local_names={"ta": "தைப்பூசம்"},
       description="Murugan festival on Pushya nakshatra in Thai."),
    _f("magha_purnima", "Magha Purnima", _lunar("Magha", "Shukla", PURNIMA),
       regions=[PAN], description="Concludes the Magha bathing month."),

    # ── Phalguna ─────────────────────────────────────────────────────────────
    _f("maha_shivaratri", "Maha Shivaratri",
       _lunar("Magha", "Krishna", 14, at="nishita"),
       regions=[PAN],
       local_names={"te": "మహా శివరాత్రి", "ta": "மகா சிவராத்திரி"},
       description="Night of Shiva. Magha Krishna Chaturdashi (amanta), Phalguna Krishna Chaturdashi (purnimanta).",
       prep="Fast and night vigil; abhishekam through the four praharas.",
       observance_note="Fixed by nishita kala (midnight), not sunrise.",
       convention_dependent=True),
    _f("holika_dahan", "Holika Dahan", _lunar("Phalguna", "Shukla", PURNIMA),
       regions=[NORTH], description="Bonfire on the eve of Holi.",
       observance_note="Lit during pradosh, avoiding Bhadra.",
       convention_dependent=True),
    _f("holi", "Holi / Dhulandi",
       _lunar("Chaitra", "Krishna", 1, reckoning="purnimanta"),
       regions=[NORTH], local_names={"hi": "होली"},
       description="Festival of colours, the day after Holika Dahan.",
       observance_note="Chaitra Krishna Pratipada (purnimanta) — under amanta "
                       "reckoning the same day is Phalguna Krishna Pratipada."),
    # ── Regional and secondary observances ───────────────────────────────────
    # A second block so the primary list above stays scannable; `occurrences`
    # sorts by date, so ordering here has no effect on output.

    # Chaitra / Panguni
    _f("chaitra_navratri", "Chaitra Navratri begins", _lunar("Chaitra", "Shukla", 1),
       regions=[NORTH], description="Nine nights of Durga, ending at Rama Navami."),
    _f("mahavir_jayanti", "Mahavir Jayanti", _lunar("Chaitra", "Shukla", 13),
       regions=[NORTH], description="Birth of Mahavira (Jain)."),
    _f("panguni_uthiram", "Panguni Uthiram", _nak_in_solar("Uttara Phalguni", 11),
       regions=[SOUTH], local_names={"ta": "பங்குனி உத்திரம்"},
       description="Uthiram in Panguni; celestial weddings at Murugan temples."),
    _f("karadaiyan_nombu", "Karadaiyan Nombu", _solar(11),
       regions=[SOUTH],
       description="Observed at the moment the Sun enters Meena.",
       observance_note="Timed to the exact Sankranti moment, which may fall at "
                       "any hour — the date alone is not the observance.",
       convention_dependent=True),

    # Vaishakha
    _f("shankara_jayanti", "Adi Shankara Jayanti", _lunar("Vaishakha", "Shukla", 5),
       regions=[SOUTH], description="Birth of Adi Shankaracharya."),
    _f("sita_navami", "Sita Navami", _lunar("Vaishakha", "Shukla", 9),
       regions=[NORTH], description="Appearance of Sita."),

    # Jyeshtha
    _f("nirjala_ekadashi", "Nirjala Ekadashi", _lunar("Jyeshtha", "Shukla", 11),
       regions=[NORTH], description="The waterless Ekadashi fast.",
       observance_note=_EKADASHI_NOTE, convention_dependent=True),
    _f("shani_jayanti", "Shani Jayanti",
       _lunar("Jyeshtha", "Krishna", AMAVASYA, reckoning="purnimanta"),
       regions=[PAN], description="Appearance of Shani."),

    # Ashadha / Aadi
    _f("devshayani_ekadashi", "Devshayani Ekadashi", _lunar("Ashadha", "Shukla", 11),
       regions=[PAN],
       description="Start of Chaturmasya; weddings pause until Kartika.",
       observance_note=_EKADASHI_NOTE, convention_dependent=True),
    _f("aadi_perukku", "Aadi Perukku", _solar(3, 18 - 1),
       regions=[SOUTH], local_names={"ta": "ஆடிப் பெருக்கு"},
       description="18th day of Aadi, honouring the rivers in spate."),
    _f("aadi_pooram", "Aadi Pooram", _nak_in_solar("Purva Phalguni", 3),
       regions=[SOUTH], description="Andal's day; Pooram in the month of Aadi.",
       observance_note="Aadi is long enough for Pooram to fall twice; the "
                       "first is taken here, and temple calendars sometimes "
                       "keep the second.",
       convention_dependent=True),

    # Shravana / Aavani
    _f("hariyali_teej", "Hariyali Teej", _lunar("Shravana", "Shukla", 3),
       regions=[NORTH], description="Monsoon Teej for Parvati."),
    _f("putrada_ekadashi", "Shravana Putrada Ekadashi",
       _lunar("Shravana", "Shukla", 11), regions=[NORTH],
       description="Observed for the wellbeing of children.",
       observance_note=_EKADASHI_NOTE, convention_dependent=True),
    _f("avani_avittam", "Avani Avittam / Upakarma",
       _lunar("Shravana", "Shukla", PURNIMA), regions=[SOUTH],
       local_names={"ta": "ஆவணி அவிட்டம்"},
       description="Annual renewal of the sacred thread.",
       observance_note="Yajur Upakarma falls on Shravana Purnima; Rig Upakarma "
                       "on Shravana nakshatra and Sama Upakarma in Bhadrapada, "
                       "so the date differs by Veda shakha.",
       convention_dependent=True),
    _f("kajari_teej", "Kajari Teej",
       _lunar("Bhadrapada", "Krishna", 3, reckoning="purnimanta"),
       regions=[NORTH], description="Teej of the Bundelkhand and Braj regions."),

    # Bhadrapada / Purattasi
    _f("hartalika_teej", "Hartalika Teej", _lunar("Bhadrapada", "Shukla", 3),
       regions=[NORTH],
       description="Fast for Parvati, the day before Ganesh Chaturthi."),
    _f("rishi_panchami", "Rishi Panchami", _lunar("Bhadrapada", "Shukla", 5),
       regions=[PAN], description="Honouring the seven rishis."),
    _f("anant_chaturdashi", "Anant Chaturdashi / Ganesh Visarjan",
       _lunar("Bhadrapada", "Shukla", 14), regions=[PAN],
       description="Immersion day closing the Ganesh festival."),
    _f("pitru_paksha_begins", "Pitru Paksha begins",
       _lunar("Bhadrapada", "Krishna", 1), regions=[PAN],
       description="Fortnight of ancestral offerings, ending at Mahalaya Amavasya.",
       observance_note="Ashwina Krishna Pratipada under purnimanta reckoning "
                       "— the same day, a different name."),
    _f("vishwakarma_puja", "Vishwakarma Puja", _solar(5), regions=[NORTH],
       description="Kanya Sankranti; tools and machinery are honoured."),

    # Ashwina / Aippasi
    _f("bathukamma_begins", "Bathukamma begins",
       _lunar("Bhadrapada", "Krishna", AMAVASYA), regions=[SOUTH],
       local_names={"te": "బతుకమ్మ"},
       description="Nine days of flower stacking in Telangana, from Mahalaya "
                   "Amavasya."),
    _f("atla_taddi", "Atla Taddi", _lunar("Ashwina", "Krishna", 3), regions=[SOUTH],
       local_names={"te": "అట్ల తద్ది"},
       description="Telugu observance for marital wellbeing; broken at moonrise.",
       observance_note=_MOONRISE_NOTE, convention_dependent=True),
    _f("ahoi_ashtami", "Ahoi Ashtami",
       _lunar("Kartika", "Krishna", 8, reckoning="purnimanta"), regions=[NORTH],
       description="Fast kept by mothers, broken at starrise.",
       observance_note="Broken at starrise or moonrise depending on the region.",
       convention_dependent=True),

    # Kartika / Kartikai
    _f("nagula_chavithi", "Nagula Chavithi", _lunar("Kartika", "Shukla", 4),
       regions=[SOUTH], local_names={"te": "నాగుల చవితి"},
       description="Serpent worship, the fourth day after Deepavali."),
    _f("skanda_sashti", "Skanda Sashti / Soorasamharam",
       _lunar("Kartika", "Shukla", 6), regions=[SOUTH],
       local_names={"ta": "கந்த சஷ்டி"},
       description="Six days of Murugan worship, closing with Soorasamharam."),
    _f("devutthana_ekadashi", "Dev Uthani Ekadashi",
       _lunar("Kartika", "Shukla", 11), regions=[NORTH],
       description="Close of Chaturmasya; the wedding season resumes.",
       observance_note=_EKADASHI_NOTE, convention_dependent=True),
    _f("guru_nanak_jayanti", "Guru Nanak Jayanti",
       _lunar("Kartika", "Shukla", PURNIMA), regions=[NORTH],
       description="Prakash Parv, on Kartika Purnima (Sikh)."),

    # Margashirsha / Margazhi
    _f("dhanurmasa_begins", "Dhanurmasam begins", _solar(8), regions=[SOUTH],
       description="Dhanu Sankranti; early-morning temple worship through "
                   "Margazhi."),
    _f("subrahmanya_shashthi", "Subrahmanya Shashthi / Champa Shashthi",
       _lunar("Margashirsha", "Shukla", 6), regions=[PAN],
       description="Murugan and Khandoba observance."),
    _f("arudra_darshan", "Arudra Darshan / Thiruvathirai",
       _nak_in_solar("Ardra", 8), regions=[SOUTH],
       local_names={"ta": "திருவாதிரை"},
       description="Nataraja darshan on Ardra in Margazhi."),
    _f("hanumath_jayanti_south", "Hanumath Jayanti (South)",
       _nak_in_solar("Moola", 8), regions=[SOUTH],
       description="Moola nakshatra in Margazhi — the southern reckoning.",
       observance_note="North India observes Hanuman Jayanti on Chaitra "
                       "Purnima instead, and Andhra keeps a third date in "
                       "Vaishakha.",
       convention_dependent=True),

    # Pausha / Thai — the Pongal and Lohri cluster
    _f("bhogi", "Bhogi", _solar(9, -1), regions=[SOUTH],
       local_names={"ta": "போகி", "te": "భోగి"},
       description="Eve of Pongal; old things are burnt and homes renewed."),
    _f("lohri", "Lohri", _solar(9, -1), regions=[NORTH],
       local_names={"pa": "ਲੋਹੜੀ"},
       description="Punjabi midwinter bonfire on the eve of Makar Sankranti."),
    _f("mattu_pongal", "Mattu Pongal / Kanuma", _solar(9, 1), regions=[SOUTH],
       local_names={"ta": "மாட்டுப் பொங்கல்", "te": "కనుమ"},
       description="Cattle are bathed, garlanded and thanked."),
    _f("kaanum_pongal", "Kaanum Pongal", _solar(9, 2), regions=[SOUTH],
       description="Family visiting day closing the Pongal sequence."),

    # Magha / Masi
    _f("mauni_amavasya", "Mauni Amavasya",
       _lunar("Magha", "Krishna", AMAVASYA, reckoning="purnimanta"),
       regions=[NORTH], description="Day of silence and river bathing."),
    _f("bhishma_ashtami", "Bhishma Ashtami", _lunar("Magha", "Shukla", 8),
       regions=[PAN], description="Tarpana offered to Bhishma."),
    _f("masi_magam", "Masi Magam", _nak_in_solar("Magha", 10), regions=[SOUTH],
       local_names={"ta": "மாசி மகம்"},
       description="Magha nakshatra in Masi; deities are taken to the water."),
]

FESTIVALS_BY_SLUG = {f["slug"]: f for f in FESTIVALS}


# ── Day scan ─────────────────────────────────────────────────────────────────

def _day_facts(day: date_cls, lat: float, lng: float, tz_str: str) -> dict | None:
    """Panchanga facts at sunrise for one day, or None if sunrise is undefined."""
    span = day_span(day.year, day.month, day.day, lat, lng, tz_str)
    if span is None:
        return None
    rise, sets, next_rise = span

    positions = sidereal_positions(rise)
    sun, moon = positions["Sun"]["lon"], positions["Moon"]["lon"]
    tithi = tithi_of(sun, moon)
    masa = amanta_masa(rise)

    # Tithi at the other two determining moments. Pradosh is taken at sunset;
    # nishita is the midpoint of the night, which is what "midnight" means in
    # this context (it tracks sunset/sunrise, not the clock).
    def _tithi_at(jd):
        p = sidereal_positions(jd)
        return tithi_of(p["Sun"]["lon"], p["Moon"]["lon"])

    pradosh = _tithi_at(sets)
    nishita = _tithi_at((sets + next_rise) / 2.0)

    return {
        "date": day,
        "jd_sunrise": rise,
        "sunrise_jd": rise,
        "sunset_jd": sets,
        "tithi_number": tithi["number"],
        "paksha": tithi["paksha"],
        "tithi_pradosh": pradosh["number"],
        "paksha_pradosh": pradosh["paksha"],
        "tithi_nishita": nishita["number"],
        "paksha_nishita": nishita["paksha"],
        "amanta_month": masa["name"].removeprefix("Adhika "),
        "purnimanta_month": masa["purnimanta_name"],
        "adhika": masa["adhika"],
        "moon_nakshatra": nakshatra_of(moon)["name"],
        "sun_sign": sign_index(sun),
        "weekday": day.weekday(),  # Monday=0 … Sunday=6
    }


def _scan_year(year: int, lat: float, lng: float, tz_str: str,
               pad_days: int = 20) -> list[dict]:
    """Sunrise facts for every day of the year, padded either side.

    The padding matters: a festival can land in early January of `year` while
    belonging to the previous lunar month, and Holi falls just after a Phalguna
    Purnima that may sit in late December.
    """
    start = date_cls(year, 1, 1) - timedelta(days=pad_days)
    end = date_cls(year, 12, 31) + timedelta(days=pad_days)

    facts, cursor = [], start
    while cursor <= end:
        row = _day_facts(cursor, lat, lng, tz_str)
        if row is not None:
            facts.append(row)
        cursor += timedelta(days=1)
    return facts


# ── Rule matching ────────────────────────────────────────────────────────────

def _month_field(rule: dict) -> str:
    return ("purnimanta_month" if rule.get("reckoning") == "purnimanta"
            else "amanta_month")


def _abs_tithi(paksha: str, number: int) -> int:
    """Tithi as 0..29 across the whole lunar month, so paksha boundaries wrap."""
    return number - 1 if paksha == "Shukla" else 14 + number


_AT_FIELDS = {
    "sunrise": ("tithi_number", "paksha"),
    "pradosh": ("tithi_pradosh", "paksha_pradosh"),
    "nishita": ("tithi_nishita", "paksha_nishita"),
}


def _match_lunar(rule: dict, facts: list[dict]) -> list[date_cls]:
    field = _month_field(rule)
    tithi_field, paksha_field = _AT_FIELDS[rule.get("at", "sunrise")]
    target = _abs_tithi(rule["paksha"], rule["tithi"])

    def _in_month(f):
        # Festivals are observed in the nija (true) month, not the intercalary
        # adhika masa — without this a leap year yields duplicate dates.
        return not f["adhika"] and f[field] == rule["month"]

    hits = [
        f["date"] for f in facts
        if _in_month(f)
        and f[paksha_field] == rule["paksha"]
        and f[tithi_field] == rule["tithi"]
    ]

    # Kshaya (skipped) tithi: a tithi shorter than a day can begin and end
    # between two sunrises, so it is current at no sunrise at all. Chaitra
    # Shukla Pratipada does exactly this in 2026, which would silently drop
    # Ugadi. The observance then falls on the day the tithi *begins*.
    #
    # Detected by the tithi index jumping by two across consecutive days. The
    # month is read from the later day, because on the earlier one the new
    # month has not begun yet. The two sets cannot overlap: if the tithi were
    # current at some sunrise, the later day would read `target`, not
    # `target + 1`. So the union is safe.
    for earlier, later in zip(facts, facts[1:]):
        if (earlier["date"] + timedelta(days=1) != later["date"]
                or not _in_month(later)):
            continue
        before = _abs_tithi(earlier[paksha_field], earlier[tithi_field])
        after = _abs_tithi(later[paksha_field], later[tithi_field])
        if (before + 1) % 30 == target and (after - 1) % 30 == target:
            hits.append(earlier["date"])

    return sorted(set(hits))


def _ingress_jd(sign: int, lo: float, hi: float) -> float:
    """Bisect for the instant the Sun crosses into ``sign``.

    Compares the signed angular distance past the cusp rather than the raw
    longitude, so the Mesha ingress (360° wrapping to 0°) behaves like the
    other eleven.
    """
    cusp = sign * 30

    def past(jd: float) -> float:
        lon = sidereal_positions(jd)["Sun"]["lon"]
        return ((lon - cusp + 180) % 360) - 180

    for _ in range(50):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if past(mid) < 0 else (lo, mid)
    return hi


def _match_solar(rule: dict, facts: list[dict]) -> list[date_cls]:
    """Sankranti, resolved by the sunset rule.

    The solar month begins on the day of the ingress when the Sun crosses the
    cusp *before* sunset, and on the following day otherwise. Taking the next
    sunrise unconditionally puts Pongal and Puthandu a day late whenever the
    ingress lands in the afternoon, as both do in 2026.
    """
    target = rule["sign"]
    hits = []
    for prev, cur in zip(facts, facts[1:]):
        if prev["sun_sign"] == target or cur["sun_sign"] != target:
            continue
        # The crossing lies between the two sunrises, i.e. within prev's day.
        jd = _ingress_jd(target, prev["sunrise_jd"], cur["sunrise_jd"])
        first = prev["date"] if jd <= prev["sunset_jd"] else cur["date"]
        hits.append(first + timedelta(days=rule.get("offset", 0)))
    return hits


def _match_nakshatra_in_solar(rule: dict, facts: list[dict]) -> list[date_cls]:
    """One date per solar-month instance the nakshatra falls in.

    Matches are grouped by month *instance*, not by sign, so the two Margazhis
    that a Gregorian year can contain each yield their own date, while a
    nakshatra recurring twice inside one month collapses to a single date.
    """
    runs: list[list[date_cls]] = []
    in_month = False
    for f in facts:
        if f["sun_sign"] != rule["sign"]:
            in_month = False
            continue
        if not in_month:
            runs.append([])
            in_month = True
        if f["moon_nakshatra"] == rule["nakshatra"]:
            runs[-1].append(f["date"])

    picked = 0 if rule.get("which", "first") == "first" else -1
    return [run[picked] for run in runs if run]


def _match_weekday_before(rule: dict, facts: list[dict]) -> list[date_cls]:
    """Last given weekday on or before the anchor tithi."""
    field = _month_field(rule)
    anchors = [
        f["date"] for f in facts
        if not f["adhika"]
        and f[field] == rule["month"]
        and f["paksha"] == rule["paksha"]
        and f["tithi_number"] == rule["tithi"]
    ]
    hits = []
    for anchor in anchors:
        back = (anchor.weekday() - rule["weekday"]) % 7
        hits.append(anchor - timedelta(days=back))
    return hits


_MATCHERS = {
    "lunar_tithi": _match_lunar,
    "solar_sankranti": _match_solar,
    "nakshatra_in_solar_month": _match_nakshatra_in_solar,
    "weekday_before_tithi": _match_weekday_before,
}


# ── Public API ───────────────────────────────────────────────────────────────

def _note_for(festival: dict, rule: dict,
              facts: list[dict]) -> tuple[str | None, bool]:
    """The festival's own note, plus any convention this run had to apply.

    Both additions below are places where more than one defensible answer
    exists, so the date is stated together with the rule that produced it
    rather than presented as the only possibility.
    """
    parts = [festival["observance_note"]] if festival["observance_note"] else []

    if rule["type"] == "solar_sankranti":
        parts.append(
            "Resolved by the sunset rule: the solar month begins on the day of "
            "the Sankranti when it occurs before sunset, otherwise the next "
            "day. Tamil, Malayalam and Punjabi almanacs differ in the cut-off "
            "they use, so a one-day difference is possible."
        )
    elif rule["type"] in ("lunar_tithi", "weekday_before_tithi"):
        field = _month_field(rule)
        if any(f["adhika"] and rule["month"] in f[field] for f in facts):
            parts.append(
                f"An adhika (intercalary) {rule['month']} falls in this year. "
                "The date given is in the nija (true) month, which is the "
                "usual rule for festivals; some traditions observe in both."
            )

    added = len(parts) > (1 if festival["observance_note"] else 0)
    return (" ".join(parts) if parts else None), added


def occurrences(year: int, *, city: str | None = None, nation: str = "IN",
                lat: float | None = None, lng: float | None = None,
                tz_str: str | None = None,
                regions: list[str] | None = None,
                slugs: list[str] | None = None) -> list[dict]:
    """Resolve festival dates for a Gregorian year at a place.

    Args:
        year: Gregorian year to resolve.
        city/nation or lat/lng/tz_str: where the sunrise is taken. Festival
            dates genuinely depend on this.
        regions: filter to any of ``"north"``, ``"south"``, ``"pan-india"``.
        slugs: restrict to specific festivals.

    Returns one row per occurrence, sorted by date. A festival can legitimately
    appear twice (or not at all) in a Gregorian year — adhika masa and the
    lunar/solar offset both cause this, and neither is an error.
    """
    lat, lng, tz_str = resolve_location(city, nation, lat, lng, tz_str)
    facts = _scan_year(year, lat, lng, tz_str)

    wanted = FESTIVALS
    if slugs is not None:
        wanted = [f for f in wanted if f["slug"] in set(slugs)]
    if regions is not None:
        keep = set(regions)
        wanted = [f for f in wanted if keep & set(f["regions"])]

    out: list[dict] = []
    for festival in wanted:
        rule = festival["rule"]
        matcher = _MATCHERS.get(rule["type"])
        if matcher is None:
            continue

        for occurs_on in matcher(rule, facts):
            # Padding lets rules resolve across year boundaries; only report
            # the requested year.
            if occurs_on.year != year:
                continue
            note, applied_convention = _note_for(festival, rule, facts)
            out.append({
                "slug": festival["slug"],
                "name": festival["name"],
                "local_names": festival["local_names"],
                "regions": festival["regions"],
                "description": festival["description"],
                "prep_guidance": festival["prep_guidance"],
                "occurs_on": occurs_on,
                "observance_note": note,
                "is_convention_dependent": (
                    festival["is_convention_dependent"] or applied_convention
                ),
                "rule": rule,
                "place": {"lat": lat, "lng": lng, "tz": tz_str,
                          "city": city, "nation": nation},
            })

    out.sort(key=lambda row: (row["occurs_on"], row["slug"]))
    return out


def upcoming(from_date: date_cls, days: int = 60, **kwargs) -> list[dict]:
    """Festivals in the next ``days`` days, spanning a year boundary if needed."""
    end = from_date + timedelta(days=days)
    rows = occurrences(from_date.year, **kwargs)
    if end.year != from_date.year:
        rows += occurrences(end.year, **kwargs)
    return [r for r in rows if from_date <= r["occurs_on"] <= end]


def catalog() -> list[dict]:
    """Festival definitions shaped for the ``festivals`` table."""
    return [
        {
            "slug": f["slug"],
            "name": f["name"],
            "name_local": (f["local_names"].get("te")
                           or f["local_names"].get("ta")
                           or f["local_names"].get("hi")),
            "language": "en",
            "region": ",".join(f["regions"]),
            "tradition": "hindu",
            "description": f["description"],
            "prep_guidance": f["prep_guidance"],
            "panchanga_rule": {
                **f["rule"],
                "observance_note": f["observance_note"],
                "is_convention_dependent": f["is_convention_dependent"],
            },
            "is_active": True,
        }
        for f in FESTIVALS
    ]
