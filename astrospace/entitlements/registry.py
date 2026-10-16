"""Canonical capability vocabulary.

This registry is policy, not storefront copy. Mobile and backend code consume
capability keys and resolved values; neither branches on store product ids.

Quantities follow the hybrid pricing decision (D2, launch plan numbers):
Free answers 3 grounded questions a month and keeps 2 profiles (D7); Plus
answers 30 and keeps 6. The "pro" tier is sold as Practitioner.

Explore depth (Hawk, 2026-10-16): Free sees the D1 chart, two yogas, every
dosha by name with its cancellations, and one compatibility score a month.
Plus adds the full yoga list, dosha explanations, full compatibility,
readings, the full remedy plan and Muhurta. Divisional charts beyond D1 are
Practitioner only. A dosha is never hidden on any plan, and no plan sells
relief from one. Question packs top up Ask beyond the monthly allowance and are
held separately (`entitlements/usage.py`). Whether a limit actually blocks is
`quotas_enforced()`: off until store purchases are live, so nobody meets a
wall with no way past it.
"""
import os
from dataclasses import dataclass
from types import MappingProxyType
from typing import Literal

AccessTier = Literal["free", "plus", "pro"]
CapabilityKind = Literal["flag", "limit"]

CATALOG_REVISION = 3


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


def _limit(key: str, description: str, *, free: int | None, plus: int | None,
           pro: int | None) -> CapabilityDefinition:
    return CapabilityDefinition(
        key=key,
        kind="limit",
        description=description,
        values=MappingProxyType({"free": free, "plus": plus, "pro": pro}),
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
    _flag("reliability.offline", "Works offline and retries when the connection drops", free=True, plus=True, pro=True, protected=True),
    _flag("profile.memory.correctness", "Readings built from your own birth details", free=True, plus=True, pro=True, protected=True),
    _flag("today.core", "Today guidance and core Panchanga", free=True, plus=True, pro=True, protected=True),
    _flag("calendar.core", "Core Calendar, set to your location", free=True, plus=True, pro=True, protected=True),
    _flag("chart.d1", "D1 chart and birth signature", free=True, plus=True, pro=True, protected=True),
    _flag("festivals.full", "Full festival packs and custom filters", free=False, plus=True, pro=True),
    _flag("vargas.full", "Divisional charts beyond D1", free=False, plus=False, pro=True),
    _flag("yogas.full", "Every yoga in the chart, not only the first two", free=False, plus=True, pro=True),
    _flag("doshas.detail", "What each dosha means and the practice that suits it", free=False, plus=True, pro=True),
    _flag("compatibility.full", "Full compatibility report beyond the score", free=False, plus=True, pro=True),
    _flag("readings.full", "Period readings and their track record", free=False, plus=True, pro=True),
    _flag("remedies.full", "The full remedy plan and practice tracker", free=False, plus=True, pro=True),
    _flag("muhurta.full", "Muhurta, finding a supportive time", free=False, plus=True, pro=True),
    _flag("dashas.full", "Full five-level Dasha navigation", free=False, plus=True, pro=True),
    _flag("transits.full", "Full transit timeline and domain detail", free=False, plus=True, pro=True),
    _flag("audio.natural_voice", "Natural server-made read-aloud voice", free=False, plus=True, pro=True),
    _flag("reports.detailed", "Detailed personal reports", free=False, plus=True, pro=True),
    _flag("practitioner.workflow", "Advanced practitioner workflow", free=False, plus=False, pro=True),
    _flag("reports.practitioner", "Practitioner report templates and export", free=False, plus=False, pro=True),
    _limit("profiles.max", "Maximum active profiles", free=2, plus=6, pro=20),
    _limit("ask.answers.period", "Grounded Ask answers per calendar month", free=3, plus=30, pro=100),
    _limit("compatibility.checks.period", "People checked for compatibility per calendar month", free=1, plus=None, pro=None),
    _unapproved_limit("compatibility.saved.max", "Maximum saved compatibility comparisons"),
)

capability_registry = MappingProxyType({item.key: item for item in _CAPABILITIES})


def quotas_enforced() -> bool:
    """Limits are counted always, and only block when this is on.

    Turned on with ASTROSPACE_QUOTAS_ENFORCED once store purchases are live,
    so the count is real from day one but no reader is stopped before there
    is a way to buy more.
    """
    return os.getenv("ASTROSPACE_QUOTAS_ENFORCED", "").lower() in {"1", "true", "yes"}


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
