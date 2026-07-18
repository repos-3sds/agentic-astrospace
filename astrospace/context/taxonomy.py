"""
Domain taxonomy loader — the data contract of the Context Engine.

The taxonomy lives in taxonomy.json so the reference corpus work can enhance
domains, subdomains, keywords and source refs without code changes. This module
validates it at load time so a bad edit fails loudly, not silently mid-reading.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from ..core.vedic.constants import PLANETS
from ..core.vedic.vargas import VARGA_FUNCTIONS

BASE = Path(__file__).parent

_VALID_KARAKA_CODES = {"AK", "AmK", "BK", "MK", "PK", "PiK", "GK", "DK"}
_VALID_ARUDHAS = {f"A{i}" for i in range(1, 13)} | {"AL", "UL"}


@dataclass(frozen=True)
class DomainSpec:
    id: str
    name: str
    description: str
    subdomains: tuple[str, ...]
    houses_primary: tuple[int, ...]
    houses_secondary: tuple[int, ...]
    karakas_naisargika: tuple[str, ...]
    karakas_jaimini: tuple[str, ...]
    vargas_primary: tuple[str, ...]
    vargas_supporting: tuple[str, ...]
    yoga_categories: tuple[str, ...]
    rule_ids: tuple[str, ...]
    arudhas: tuple[str, ...]
    gochara_planets: tuple[str, ...]
    keywords: tuple[str, ...]
    convention_flags: tuple[str, ...] = field(default=())
    exclusions: tuple[str, ...] = field(default=())
    source_refs: tuple[str, ...] = field(default=())

    @property
    def all_houses(self) -> tuple[int, ...]:
        return tuple(dict.fromkeys([*self.houses_primary, *self.houses_secondary]))

    @property
    def all_vargas(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys([*self.vargas_primary, *self.vargas_supporting]))


class TaxonomyError(ValueError):
    """taxonomy.json failed validation."""


def _validate(domain_id: str, spec: DomainSpec) -> None:
    for house in spec.all_houses:
        if not 1 <= house <= 12:
            raise TaxonomyError(f"{domain_id}: house {house} out of range 1-12")
    for planet in [*spec.karakas_naisargika, *spec.gochara_planets]:
        if planet not in PLANETS:
            raise TaxonomyError(f"{domain_id}: unknown planet {planet!r}")
    for code in spec.karakas_jaimini:
        if code not in _VALID_KARAKA_CODES:
            raise TaxonomyError(f"{domain_id}: unknown Jaimini karaka {code!r}")
    for varga in spec.all_vargas:
        if varga not in VARGA_FUNCTIONS:
            raise TaxonomyError(f"{domain_id}: unknown varga {varga!r}")
    for arudha in spec.arudhas:
        if arudha not in _VALID_ARUDHAS:
            raise TaxonomyError(f"{domain_id}: unknown arudha {arudha!r}")
    if not spec.keywords:
        raise TaxonomyError(f"{domain_id}: keywords must not be empty (router fallback)")
    if not spec.description:
        raise TaxonomyError(f"{domain_id}: description must not be empty (LLM router)")


def _spec_from_json(domain_id: str, raw: dict) -> DomainSpec:
    spec = DomainSpec(
        id=domain_id,
        name=raw["name"],
        description=raw["description"],
        subdomains=tuple(raw.get("subdomains", [])),
        houses_primary=tuple(raw["houses"]["primary"]),
        houses_secondary=tuple(raw["houses"].get("secondary", [])),
        karakas_naisargika=tuple(raw["karakas"].get("naisargika", [])),
        karakas_jaimini=tuple(raw["karakas"].get("jaimini", [])),
        vargas_primary=tuple(raw["vargas"].get("primary", [])),
        vargas_supporting=tuple(raw["vargas"].get("supporting", [])),
        yoga_categories=tuple(raw.get("yoga_categories", [])),
        rule_ids=tuple(raw.get("rule_ids", [])),
        arudhas=tuple(raw.get("arudhas", [])),
        gochara_planets=tuple(raw.get("gochara_planets", [])),
        keywords=tuple(raw.get("keywords", [])),
        convention_flags=tuple(raw.get("convention_flags", [])),
        exclusions=tuple(raw.get("exclusions", [])),
        source_refs=tuple(raw.get("source_refs", [])),
    )
    _validate(domain_id, spec)
    return spec


@lru_cache(maxsize=1)
def taxonomy() -> dict[str, DomainSpec]:
    payload = json.loads((BASE / "taxonomy.json").read_text())
    return {
        domain_id: _spec_from_json(domain_id, raw)
        for domain_id, raw in payload["domains"].items()
    }


@lru_cache(maxsize=1)
def taxonomy_version() -> int:
    return json.loads((BASE / "taxonomy.json").read_text()).get("version", 0)


def get_domain(domain_id: str) -> DomainSpec:
    try:
        return taxonomy()[domain_id]
    except KeyError:
        raise TaxonomyError(
            f"Unknown domain {domain_id!r}; options: {sorted(taxonomy())}"
        )


def domain_ids() -> list[str]:
    return list(taxonomy())
