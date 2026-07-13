"""
VedicChart — single entry point that assembles the full Vedic payload:
positions, panchanga, all vargas, dignities, Avkahada Chakra, Ghatak,
and favourable points.
"""
from datetime import datetime

from .positions import (
    birth_moment, sidereal_positions, sidereal_lagna, tropical_sun,
    ayanamsha_value, local_mean_time, local_sidereal_time, obliquity,
    sign_index, sign_name, sign_name_sanskrit, sign_lord, degree_in_sign,
    to_dms, house_from_lagna,
)
from .nakshatra import nakshatra_of
from .panchanga import panchanga_of
from .vargas import VARGA_FUNCTIONS, VARGA_INFO, UNVERIFIED_VARGAS
from .strength import all_dignities, planetary_conditions, shadbala
from .avkahada import avkahada_chakra
from .ghatak import ghatak_of
from .favourable import favourable_points
from .dashas import vimshottari_dasha
from .ashtakavarga import ashtakavarga
from .doshas import dosha_summary
from .yogas import yoga_summary
from .transits import transit_analysis
from .calendar import calendar_intelligence


class VedicChart:
    def __init__(self, name: str, year: int, month: int, day: int,
                 hour: int, minute: int, city: str = None, nation: str = "IN",
                 lat: float = None, lng: float = None, tz_str: str = None,
                 ayanamsha: str = "lahiri", node_type: str = "mean"):
        self.name = name
        self.birth_day_of_month = day
        self.city = city
        self.ayanamsha = ayanamsha
        self.node_type = node_type

        self.moment = birth_moment(year, month, day, hour, minute,
                                   city, nation, lat, lng, tz_str)
        self.positions = sidereal_positions(self.moment.jd_ut, ayanamsha, node_type)
        self.lagna_lon = sidereal_lagna(self.moment.jd_ut, self.moment.lat,
                                        self.moment.lng, ayanamsha)
        self.tropical_sun_lon = tropical_sun(self.moment.jd_ut)
        self.panchanga = panchanga_of(
            self.moment, self.positions["Sun"]["lon"], self.positions["Moon"]["lon"],
        )

    # ── sections ─────────────────────────────────────────────────────────────

    def meta(self) -> dict:
        m = self.moment
        ayan = ayanamsha_value(m.jd_ut, self.ayanamsha)
        lmt = local_mean_time(m)
        lst = local_sidereal_time(m.jd_ut, m.lng)
        lst_h = int(lst)
        lst_m = int((lst - lst_h) * 60)
        lst_s = int(round(((lst - lst_h) * 60 - lst_m) * 60))
        return {
            "name": self.name,
            "birth_date": m.dt_local.strftime("%Y-%m-%d"),
            "birth_time": m.dt_local.strftime("%H:%M"),
            "weekday": m.dt_local.strftime("%A"),
            "place": self.city,
            "latitude": m.lat,
            "longitude": m.lng,
            "timezone": m.tz_str,
            "julian_day_ut": m.jd_ut,
            "ayanamsha": {"name": self.ayanamsha.title(), "value": ayan, "dms": to_dms(ayan)},
            "node_type": self.node_type,
            "local_mean_time": lmt.strftime("%H:%M:%S"),
            "sidereal_time": f"{lst_h}:{lst_m:02d}:{lst_s:02d}",
            "obliquity": round(obliquity(m.jd_ut), 4),
        }

    def planet_details(self) -> dict:
        lagna_sign = sign_index(self.lagna_lon)
        out = {}
        for planet, data in self.positions.items():
            lon = data["lon"]
            s = sign_index(lon)
            nak = nakshatra_of(lon)
            out[planet] = {
                "longitude": round(lon, 4),
                "sign": sign_name(s),
                "sign_sanskrit": sign_name_sanskrit(s),
                "sign_lord": sign_lord(s),
                "degree_in_sign": round(degree_in_sign(lon), 4),
                "dms": to_dms(degree_in_sign(lon)),
                "house": house_from_lagna(s, lagna_sign),
                "nakshatra": nak["name"],
                "nakshatra_pada": nak["pada"],
                "nakshatra_lord": nak["lord"],
                "retrograde": data["retrograde"],
                "speed": round(data["speed"], 6),
            }
        return out

    def lagna_details(self) -> dict:
        s = sign_index(self.lagna_lon)
        nak = nakshatra_of(self.lagna_lon)
        return {
            "longitude": round(self.lagna_lon, 4),
            "sign": sign_name(s),
            "sign_sanskrit": sign_name_sanskrit(s),
            "lord": sign_lord(s),
            "degree_in_sign": round(degree_in_sign(self.lagna_lon), 4),
            "dms": to_dms(degree_in_sign(self.lagna_lon)),
            "nakshatra": nak["name"],
            "nakshatra_pada": nak["pada"],
        }

    def varga_chart(self, varga: str) -> dict:
        fn = VARGA_FUNCTIONS[varga]
        lagna_sign = fn(self.lagna_lon)
        planets = {}
        d1_signs = {p: sign_index(d["lon"]) for p, d in self.positions.items()}
        for planet, data in self.positions.items():
            s = fn(data["lon"])
            planets[planet] = {
                "sign": sign_name(s),
                "sign_sanskrit": sign_name_sanskrit(s),
                "sign_index": s,
                "house": house_from_lagna(s, lagna_sign),
                "retrograde": data["retrograde"],
                "vargottama": varga == "D9" and s == d1_signs[planet],
            }
        return {
            "varga": varga,
            **VARGA_INFO[varga],
            "verified_rule": varga not in UNVERIFIED_VARGAS,
            "lagna": {
                "sign": sign_name(lagna_sign),
                "sign_sanskrit": sign_name_sanskrit(lagna_sign),
                "sign_index": lagna_sign,
            },
            "planets": planets,
        }

    def all_varga_charts(self) -> dict:
        return {v: self.varga_chart(v) for v in VARGA_FUNCTIONS}

    def avkahada(self) -> dict:
        return avkahada_chakra(self.lagna_lon, self.positions["Moon"]["lon"],
                               self.tropical_sun_lon, self.panchanga)

    def ghatak(self) -> dict:
        return ghatak_of(sign_index(self.positions["Moon"]["lon"]))

    def favourable(self) -> dict:
        return favourable_points(self.birth_day_of_month, sign_index(self.lagna_lon))

    def dignities(self) -> dict:
        return all_dignities(self.positions)

    def shadbala(self) -> dict:
        return shadbala(self.positions, self.lagna_lon)

    def planetary_conditions(self) -> dict:
        return planetary_conditions(self.positions)

    def dashas(self) -> dict:
        as_of = datetime.now(self.moment.dt_local.tzinfo)
        return vimshottari_dasha(
            self.positions["Moon"]["lon"], self.moment.dt_local, as_of,
        )

    def ashtakavarga(self) -> dict:
        return ashtakavarga(self.positions, self.lagna_lon)

    def doshas(self) -> dict:
        return dosha_summary(self.positions, self.lagna_lon)

    def yogas(self) -> dict:
        return yoga_summary(self.positions, self.lagna_lon)

    def transits(self) -> dict:
        as_of = datetime.now(self.moment.dt_local.tzinfo)
        return transit_analysis(
            self.positions,
            self.lagna_lon,
            as_of,
            self.ayanamsha,
            self.node_type,
        )

    def calendar_intelligence(self, as_of: datetime = None,
                              city: str = None, nation: str = None,
                              lat: float = None, lng: float = None,
                              tz_str: str = None, display_tz_str: str = None,
                              days: int = 30) -> dict:
        as_of = as_of or datetime.now(self.moment.dt_local.tzinfo)
        return calendar_intelligence(
            self,
            as_of,
            city or self.city,
            nation or "IN",
            self.moment.lat if lat is None else lat,
            self.moment.lng if lng is None else lng,
            tz_str or self.moment.tz_str,
            display_tz_str or tz_str or self.moment.tz_str,
            days,
        )

    def transit_context(self) -> dict:
        now = datetime.now(self.moment.dt_local.tzinfo)
        transit = VedicChart(
            "Current Transits",
            now.year,
            now.month,
            now.day,
            now.hour,
            now.minute,
            city=self.city,
            lat=self.moment.lat,
            lng=self.moment.lng,
            tz_str=self.moment.tz_str,
            ayanamsha=self.ayanamsha,
            node_type=self.node_type,
        )
        natal_lagna_sign = sign_index(self.lagna_lon)
        natal_moon_sign = sign_index(self.positions["Moon"]["lon"])
        gochara = {}
        for planet, data in transit.positions.items():
            s = sign_index(data["lon"])
            nak = nakshatra_of(data["lon"])
            gochara[planet] = {
                "longitude": round(data["lon"], 4),
                "sign": sign_name(s),
                "degree_in_sign": round(degree_in_sign(data["lon"]), 4),
                "dms": to_dms(degree_in_sign(data["lon"])),
                "nakshatra": nak["name"],
                "nakshatra_pada": nak["pada"],
                "house_from_lagna": house_from_lagna(s, natal_lagna_sign),
                "house_from_moon": house_from_lagna(s, natal_moon_sign),
                "retrograde": data["retrograde"],
            }

        saturn_house = gochara["Saturn"]["house_from_moon"]
        return {
            "as_of": transit.meta(),
            "natal": {
                "rashi": self.varga_chart("D1"),
                "navamsha": self.varga_chart("D9"),
            },
            "transit": {
                "rashi": transit.varga_chart("D1"),
                "navamsha": transit.varga_chart("D9"),
            },
            "gochara": gochara,
            "sade_sati": {
                "active": saturn_house in (12, 1, 2),
                "phase": {12: "first", 1: "second", 2: "third"}.get(saturn_house),
                "saturn_house_from_moon": saturn_house,
            },
        }

    def to_dict(self) -> dict:
        return {
            "meta": self.meta(),
            "lagna": self.lagna_details(),
            "planets": self.planet_details(),
            "panchanga": self.panchanga,
            "avkahada": self.avkahada(),
            "ghatak": self.ghatak(),
            "favourable": self.favourable(),
            "dignities": self.dignities(),
            "planetary_conditions": self.planetary_conditions(),
            "shadbala": self.shadbala(),
            "vargas": self.all_varga_charts(),
            "doshas": self.doshas(),
            "yogas": self.yogas(),
        }
