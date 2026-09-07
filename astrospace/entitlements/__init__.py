"""Server-authoritative commercial entitlement resolution."""

from .registry import CATALOG_REVISION, capability_registry
from .resolver import (
    EntitlementDecision,
    EntitlementDenied,
    EntitlementSnapshot,
    require_entitlement,
    resolve_entitlements,
)

__all__ = [
    "CATALOG_REVISION",
    "EntitlementDecision",
    "EntitlementDenied",
    "EntitlementSnapshot",
    "capability_registry",
    "require_entitlement",
    "resolve_entitlements",
]
