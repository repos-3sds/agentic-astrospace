"""One answer to "where and in whose clock are today's windows computed?"

Three routes (calendar intelligence, personal panchanga, muhurta) each
resolved the place on their own, and two of them disagreed: Calendar Day
took a representative city for the viewer's timezone while Muhurta took the
birth city, so the same build showed Brahma Muhurta at 23:00 on one screen
and 04:35 on the other. This module is the single rule, and every payload
built from it says which branch was taken so the screen can label it.

The rule, in order:

1. an explicit ``city``/``nation`` (the panchanga place the user picked);
2. otherwise, when a viewer ``timezone`` is given that is not the birth
   city's own and the offline city table has a city in it, that city —
   "where the phone is", to a first order (a zone names a country, not a
   town, so within the birth city's zone the birth city is the better guess);
3. otherwise the kundli's birth city.

Windows are always rendered in the place's own clock, the way Today already
did: a sunrise-relative window has no meaning in another city's time. The
viewer timezone only picks the city (rule 2) and decides what "today" is.
The payload names the place, its timezone and which rule chose it, so every
screen can say "Hyderabad (birth city) · GMT+5:30" instead of implying the
times are local to the phone.

Lives with the context engine, not the API, because the notification worker
uses the same rule (audit I8): it raises PlaceNotFound, and the routers'
wrapper in api/timing_place.py turns that into a 422.
"""
from dataclasses import dataclass

from ..core.cities import canonical_timezone, city_for_timezone, lookup_city

SOURCE_SELECTED = "selected"
SOURCE_VIEWER_TIMEZONE = "viewer_timezone"
SOURCE_BIRTH_CITY = "birth_city"


class PlaceNotFound(ValueError):
    """The chosen city is not in the offline table."""


@dataclass(frozen=True)
class TimingPlace:
    city: str
    nation: str
    lat: float
    lng: float
    tz_str: str
    viewer_tz: str | None
    source: str

    @property
    def today_tz(self) -> str:
        """The clock that decides which calendar day is "today"."""
        return self.viewer_tz or self.tz_str

    def as_payload(self) -> dict:
        return {
            "city": self.city,
            "nation": self.nation,
            "timezone": self.tz_str,
            "source": self.source,
            "viewer_timezone": self.viewer_tz,
        }


def validate_timezone(tz_str: str | None, fallback: str) -> str:
    """The viewer's zone under its current name, or ``fallback``.

    The zone comes from the phone, not from anything the reader typed, so a
    name the server cannot read is dropped rather than refused: the place
    falls through to the next rule (the birth city) and the screen still
    loads. Refusing it once showed testers "We couldn't work out the time
    zone" on every Muhurta search, with nothing they could change.
    """
    return canonical_timezone(tz_str) or fallback


def resolve_timing_place(kundli, timezone: str | None = None,
                         city: str | None = None, nation: str | None = None) -> TimingPlace:
    viewer_tz = validate_timezone(timezone, "") or None
    birth_geo = None
    if not city and viewer_tz:
        birth_geo = lookup_city(kundli.birth_city, kundli.birth_nation)
    if city:
        loc_city, loc_nation, source = city, nation or kundli.birth_nation, SOURCE_SELECTED
    elif birth_geo and birth_geo[2] == viewer_tz:
        # The zone says the phone is in the birth city's country, and the
        # birth city is a better guess at the town than the first city the
        # table lists for the zone (Mumbai, for every Indian reader): Rahu
        # Kalam in Kolkata starts an hour before Mumbai's.
        loc_city, loc_nation, source = kundli.birth_city, kundli.birth_nation, SOURCE_BIRTH_CITY
    else:
        viewer_city = city_for_timezone(viewer_tz) if viewer_tz else None
        if viewer_city:
            loc_city, loc_nation, source = viewer_city[0], viewer_city[1], SOURCE_VIEWER_TIMEZONE
        else:
            loc_city, loc_nation, source = kundli.birth_city, kundli.birth_nation, SOURCE_BIRTH_CITY
    geo = lookup_city(loc_city, loc_nation)
    if not geo:
        raise PlaceNotFound(f"City {loc_city!r} not in offline database.")
    lat, lng, tz_str = geo
    return TimingPlace(loc_city, loc_nation, lat, lng, tz_str, viewer_tz, source)
