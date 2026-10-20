"""Server-authoritative commercial entitlement resolution."""

from .registry import CATALOG_REVISION, capability_registry
from .resolver import (
    EntitlementDecision,
    EntitlementDenied,
    EntitlementSnapshot,
    plan_lock,
    require_entitlement,
    require_plan,
    resolve_entitlements,
)

__all__ = [
    "CATALOG_REVISION",
    "EntitlementDecision",
    "EntitlementDenied",
    "EntitlementSnapshot",
    "capability_registry",
    "plan_lock",
    "require_entitlement",
    "require_plan",
    "resolve_entitlements",
]
