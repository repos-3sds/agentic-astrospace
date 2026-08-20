"""Canonical capability vocabulary.

This registry is policy, not storefront copy. Mobile and backend code consume
capability keys and resolved values; neither branches on store product ids.
Commercial quantities remain unset until CE-1 approves economics.
"""
from dataclasses import dataclass
from types import MappingProxyType
from typing import Literal

AccessTier = Literal["free", "plus", "pro"]
CapabilityKind = Literal["flag", "limit"]

CATALOG_REVISION = 1


@dataclass(frozen=True)
class CapabilityDefinition:
    key: str
    kind: CapabilityKind
    description: str
    values: MappingProxyType
    protected_baseline: bool = False

    def value_for(self, tier: AccessTier):
        return self.values[tier]


def _flag(key: str, description: str, *, free: bool, plus: bool, pro: bool,
          protected: bool = False) -> CapabilityDefinition:
    return CapabilityDefinition(
        key=key,
        kind="flag",
        description=description,
        values=MappingProxyType({"free": free, "plus": plus, "pro": pro}),
        protected_baseline=protected,
    )


def _unapproved_limit(key: str, description: str) -> CapabilityDefinition:
    # None means "not commercially enforced", not unlimited. CE-1 must replace
    # these through reviewed policy before a gate may consume them.
    return CapabilityDefinition(
        key=key,
        kind="limit",
        description=description,
        values=MappingProxyType({"free": None, "plus": None, "pro": None}),
    )


_CAPABILITIES = (
    _flag("safety.guidance", "Safety and refer-out guidance", free=True, plus=True, pro=True, protected=True),
    _flag("sources.provenance", "Sources and reading provenance", free=True, plus=True, pro=True, protected=True),
    _flag("account.controls", "Account correction, export and deletion", free=True, plus=True, pro=True, protected=True),
    _flag("reliability.offline", "Baseline offline and retry behavior", free=True, plus=True, pro=True, protected=True),
    _flag("profile.memory.correctness", "Profile context needed for truthful readings", free=True, plus=True, pro=True, protected=True),
    _flag("today.core", "Today guidance and core Panchanga", free=True, plus=True, pro=True, protected=True),
    _flag("calendar.core", "Core Calendar and location correctness", free=True, plus=True, pro=True, protected=True),
    _flag("chart.d1", "D1 chart and birth signature", free=True, plus=True, pro=True, protected=True),
    _flag("festivals.full", "Full festival packs and custom filters", free=False, plus=True, pro=True),
    _flag("vargas.full", "Full standard divisional-chart set", free=False, plus=True, pro=True),
    _flag("dashas.full", "Full five-level Dasha navigation", free=False, plus=True, pro=True),
    _flag("transits.full", "Full transit timeline and domain detail", free=False, plus=True, pro=True),
    _flag("reports.detailed", "Detailed personal reports", free=False, plus=True, pro=True),
    _flag("practitioner.workflow", "Advanced practitioner workflow", free=False, plus=False, pro=True),
    _flag("reports.practitioner", "Practitioner report templates and export", free=False, plus=False, pro=True),
    _unapproved_limit("profiles.max", "Maximum active profiles"),
    _unapproved_limit("ask.answers.period", "Grounded Ask answers per server-defined period"),
    _unapproved_limit("compatibility.saved.max", "Maximum saved compatibility comparisons"),
)

capability_registry = MappingProxyType({item.key: item for item in _CAPABILITIES})


def public_registry() -> dict:
    return {
        "revision": CATALOG_REVISION,
        "capabilities": {
            key: {
                "kind": definition.kind,
                "description": definition.description,
                "protected_baseline": definition.protected_baseline,
            }
            for key, definition in capability_registry.items()
        },
    }
