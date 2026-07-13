"""
Ghatak Chakra — inauspicious indicators keyed by janma rashi (Moon sign).

Month/tithi/day/nakshatra/lagna columns follow the standard published
Ghatak table; the ghatak Moon sign is the 4th from the janma rashi per
common tables. Yoga, karana and prahar columns are intentionally None —
no verified source yet, and shipping a guess for an "inauspicious"
indicator is worse than shipping nothing. VERIFY all on reference chart.
"""
from .constants import GHATAK_CHAKRA, TITHI_GROUPS
from .positions import sign_name, sign_name_sanskrit


def ghatak_of(moon_sign: int) -> dict:
    month, tithi_group, day, nakshatra, lagna_idx = GHATAK_CHAKRA[moon_sign % 12]
    chandra_idx = (moon_sign + 3) % 12  # 4th from janma rashi
    return {
        "rashi": sign_name(chandra_idx),
        "rashi_sanskrit": sign_name_sanskrit(chandra_idx),
        "month": month,
        "tithi": ", ".join(str(t) for t in TITHI_GROUPS[tithi_group]),
        "tithi_group": tithi_group,
        "day": day,
        "nakshatra": nakshatra,
        "lagna": sign_name(lagna_idx),
        "lagna_sanskrit": sign_name_sanskrit(lagna_idx),
        "yoga": None,      # pending verified source
        "karana": None,    # pending verified source
        "prahar": None,    # pending verified source
    }
