"""
VedicChart — single entry point that assembles the full Vedic payload:
positions, panchanga, all vargas, dignities, Avkahada Chakra, Ghatak,
and favourable points.
"""
from datetime import datetime

from .positions import (
    birth_moment, sidereal_positions, sidereal_lagna, sidereal_mc, tropical_sun,
    ayanamsha_value, local_mean_time, local_sidereal_time, obliquity,
    sign_index, sign_name, sign_name_sanskrit, sign_lord, degree_in_sign,
    to_dms, house_from_lagna, sunrise_jd,
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
from .gocharam import gochara_rules, gocharam_profile
from .calendar import calendar_intelligence
from .jaimini import chara_karakas, arudha_padas, arudha_lagna, upapada
from .special_lagnas import (
    special_lagnas as special_lagnas_of,
    bhrigu_bindu as bhrigu_bindu_of,
    indu_lagna as indu_lagna_of,
    GHATI_MINUTES,
)
from .shayanadi import all_shayanadi_avasthas
from .argala import all_argala
from .yogini import yogini_dasha
from .vimshopaka import vimshopaka_bala as vimshopaka_bala_of
from .chara_dasha import chara_dasha as chara_dasha_of
from .bhava_chalit import bhava_chalit as bhava_chalit_of
from .masa import amanta_masa, samvatsara, ritu, ayana


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

    def provenance(self, context: str = "natal") -> dict:
        """Calculation conventions and trust status for downstream display."""
        return {
            "context": context,
            "engine": "Swiss Ephemeris via pyswisseph",
            "zodiac": "sidereal",
            "ayanamsha": self.ayanamsha,
            "node_type": self.node_type,
            "house_system": "whole-sign houses from sidereal lagna",
            "lagna_method": "Swiss Ephemeris sidereal ascendant",
            "timezone": self.moment.tz_str,
            "calculation_place": {
                "city": self.city,
                "latitude": self.moment.lat,
                "longitude": self.moment.lng,
            },
            "confidence": {
                "planetary_positions": "computed",
                "panchanga": "computed",
                "dashas": "computed from Moon nakshatra",
                "vargas": "mixed: classical vargas verified; rare vargas flagged",
                "yogas_doshas": "rule-based interpretation",
                "strength": "v1 approximation where marked",
            },
            "notes": [
                "Planetary longitudes are sidereal degrees.",
                "Houses are counted whole-sign from the lagna sign.",
                "Interpretive rules may vary by parampara; convention-dependent items are flagged.",
            ],
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
            "provenance": {
                **self.provenance(f"varga:{varga}"),
                "varga_rule_status": "verified" if varga not in UNVERIFIED_VARGAS else "needs source verification",
            },
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
        lagna_sign = sign_index(self.lagna_lon)
        moon_lon = self.positions["Moon"]["lon"]
        nak = nakshatra_of(moon_lon)
        atmakaraka = self.jaimini()["chara_karakas"]["karakas"]["AK"]["planet"]
        return favourable_points(
            self.birth_day_of_month, lagna_sign,
            moon_sign=sign_index(moon_lon), nakshatra_lord=nak["lord"],
            atmakaraka=atmakaraka,
        )

    def dignities(self) -> dict:
        return all_dignities(self.positions)

    def shadbala(self) -> dict:
        # Already includes the degree-precise BPHS virupa Shadbala (T0.5,
        # docs/backend_astro_depth_checklist_2026-08-06.md) under the
        # "classical" key whenever moment/ayanamsha_val are supplied, as
        # they are here — see strength.shadbala()'s own docstring.
        return shadbala(
            self.positions,
            self.lagna_lon,
            moment=self.moment,
            ayanamsha_val=ayanamsha_value(self.moment.jd_ut, self.ayanamsha),
        )

    def planetary_conditions(self) -> dict:
        return planetary_conditions(self.positions)

    def planet_annotations(self) -> dict:
        dignities = self.dignities()
        conditions = self.planetary_conditions()["rows"]
        annotations = {}
        for planet, position in self.positions.items():
            rows = []
            dignity = dignities.get(planet, {}).get("dignity")
            if dignity == "Exalted":
                rows.append({"code": "exalted", "symbol": "↑", "label": "Exalted", "tone": "good"})
            elif dignity == "Debilitated":
                rows.append({"code": "debilitated", "symbol": "↓", "label": "Debilitated", "tone": "bad"})
            if position.get("retrograde"):
                rows.append({"code": "retrograde", "symbol": "↺", "label": "Retrograde", "tone": "neutral"})
            if conditions.get(planet, {}).get("combustion", {}).get("active"):
                rows.append({"code": "combust", "symbol": "☼", "label": "Combust", "tone": "warn"})
            annotations[planet] = rows
        return annotations

    def dashas(self, as_of: datetime = None) -> dict:
        as_of = as_of or datetime.now(self.moment.dt_local.tzinfo)
        return vimshottari_dasha(
            self.positions["Moon"]["lon"], self.moment.dt_local, as_of,
        )

    def yogini_dashas(self) -> dict:
        as_of = datetime.now(self.moment.dt_local.tzinfo)
        return yogini_dasha(
            self.positions["Moon"]["lon"], self.moment.dt_local, as_of,
        )

    def jaimini(self) -> dict:
        lagna_sign = sign_index(self.lagna_lon)
        return {
            "chara_karakas": chara_karakas(self.positions),
            "arudha_lagna": arudha_lagna(lagna_sign, self.positions),
            "upapada": upapada(lagna_sign, self.positions),
            "arudha_padas": arudha_padas(lagna_sign, self.positions),
        }

    def chara_dasha(self, as_of: datetime = None) -> dict:
        as_of = as_of or datetime.now(self.moment.dt_local.tzinfo)
        lagna_sign = sign_index(self.lagna_lon)
        return chara_dasha_of(lagna_sign, self.positions, self.moment.dt_local, as_of)

    def _vedic_day_sunrise_jd(self) -> float | None:
        """Sunrise (UT jd) of the Vedic day containing the birth: the last
        sunrise at or before the birth instant."""
        m = self.moment
        rise = sunrise_jd(m.jd_ut - 1.5, m.lat, m.lng)
        if rise is None or rise > m.jd_ut:
            return None
        while True:
            nxt = sunrise_jd(rise + 0.01, m.lat, m.lng)
            if nxt is None or nxt > m.jd_ut:
                return rise
            rise = nxt

    def special_lagnas(self) -> dict:
        # bhava_lagna/hora_lagna/ghati_lagna stay top-level exactly as
        # before (ui/src/app/core/models.ts SpecialLagnasPayload and the
        # Jaimini/Strength-Advanced screens read them there) — new points
        # are added as new top-level keys, not by restructuring the payload.
        rise = self._vedic_day_sunrise_jd()
        if rise is None:
            out = {"error": "Sunrise undefined at this latitude/date (circumpolar)."}
        else:
            sun_at_rise = sidereal_positions(rise, self.ayanamsha, self.node_type)["Sun"]["lon"]
            out = special_lagnas_of(self.moment.jd_ut, rise, sun_at_rise, self.lagna_lon)

        lagna_sign = sign_index(self.lagna_lon)
        moon_sign = sign_index(self.positions["Moon"]["lon"])
        out["bhrigu_bindu"] = bhrigu_bindu_of(self.positions["Rahu"]["lon"], self.positions["Moon"]["lon"])
        out["indu_lagna"] = indu_lagna_of(lagna_sign, moon_sign, self.positions)
        return out

    def shayanadi_avasthas(self) -> dict:
        rise = self._vedic_day_sunrise_jd()
        if rise is None:
            return {"error": "Sunrise undefined at this latitude/date (circumpolar)."}
        hours = (self.moment.jd_ut - rise) * 24.0
        ghatis = hours * 60.0 / GHATI_MINUTES
        lagna_sign = sign_index(self.lagna_lon)
        return all_shayanadi_avasthas(self.positions, lagna_sign, ghatis)

    def argala(self) -> dict:
        lagna_sign = sign_index(self.lagna_lon)
        return all_argala(lagna_sign, self.positions)

    def masa(self) -> dict:
        jd = self.moment.jd_ut
        m = amanta_masa(jd)
        return {
            **m,
            "samvatsara": samvatsara(jd),
            "ritu": ritu(m["name_index"]),
            "ayana": ayana(jd),
        }

    def ashtakavarga(self) -> dict:
        return ashtakavarga(self.positions, self.lagna_lon)

    def vimshopaka_bala(self, scheme: str = "shodashavarga") -> dict:
        return vimshopaka_bala_of(self.positions, scheme=scheme)

    def bhava_chalit(self) -> dict:
        """Sripati (Bhava Chalit) houses — an opt-in alternate lens next to
        this chart's default whole-sign houses. See bhava_chalit.py."""
        mc = sidereal_mc(self.moment.jd_ut, self.moment.lat, self.moment.lng, self.ayanamsha)
        return bhava_chalit_of(self.lagna_lon, mc, self.positions)

    def doshas(self) -> dict:
        return dosha_summary(self.positions, self.lagna_lon)

    def yogas(self) -> dict:
        return yoga_summary(self.positions, self.lagna_lon)

    def transits(self) -> dict:
        as_of = datetime.now(self.moment.dt_local.tzinfo)
        dasha_context = self.dashas().get("current")
        return transit_analysis(
            self.positions,
            self.lagna_lon,
            as_of,
            self.ayanamsha,
            self.node_type,
            dasha_context=dasha_context,
        )

    def gocharam(self, scan_days: int = 90, as_of: datetime = None) -> dict:
        as_of = as_of or datetime.now(self.moment.dt_local.tzinfo)
        dasha_context = self.dashas(as_of=as_of).get("current")
        return gocharam_profile(
            self.positions,
            self.lagna_lon,
            as_of,
            self.ayanamsha,
            self.node_type,
            past_days=scan_days,
            future_days=scan_days,
            dasha_context=dasha_context,
        )

    def calendar_intelligence(self, as_of: datetime = None,
                              city: str = None, nation: str = None,
                              lat: float = None, lng: float = None,
                              tz_str: str = None, display_tz_str: str = None,
                              days: int = 30,
                              include_practitioner_detail: bool = False) -> dict:
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
            include_practitioner_detail=include_practitioner_detail,
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
        gochara_analysis = gochara_rules(
            transit.positions,
            self.positions,
            natal_lagna_sign,
            natal_moon_sign,
        )
        return {
            "as_of": transit.meta(),
            "provenance": self.provenance("transit-context"),
            "planet_annotations": {
                "natal": self.planet_annotations(),
                "transit": transit.planet_annotations(),
            },
            "natal": {
                "rashi": self.varga_chart("D1"),
                "navamsha": self.varga_chart("D9"),
            },
            "transit": {
                "rashi": transit.varga_chart("D1"),
                "navamsha": transit.varga_chart("D9"),
            },
            # Keep the historical planet-map field while exposing the canonical
            # rule payload for newer consumers.
            "gochara": gochara_analysis["planets"],
            "gochara_analysis": gochara_analysis,
            "sade_sati": gochara_analysis["sade_sati"],
        }

    def to_dict(self) -> dict:
        return {
            "meta": self.meta(),
            "provenance": self.provenance("natal"),
            "lagna": self.lagna_details(),
            "planets": self.planet_details(),
            "panchanga": self.panchanga,
            "avkahada": self.avkahada(),
            "ghatak": self.ghatak(),
            "favourable": self.favourable(),
            "dignities": self.dignities(),
            "planetary_conditions": self.planetary_conditions(),
            "planet_annotations": self.planet_annotations(),
            "shadbala": self.shadbala(),
            "vargas": self.all_varga_charts(),
            "doshas": self.doshas(),
            "yogas": self.yogas(),
            "jaimini": self.jaimini(),
            "special_lagnas": self.special_lagnas(),
            "shayanadi_avasthas": self.shayanadi_avasthas(),
            "argala": self.argala(),
            "masa": self.masa(),
        }
