"""Deterministic Gocharam module.

South-Indian practice is treated as Moon-first with Lagna cross-checks. The
module generates rule windows and plain-language readings without AI.
"""

from .rules import CLASSICAL_GOCHARA_VEDHA, VEDHA_EXEMPT_PAIRS, classical_gochara_status
from .timeline import gocharam_profile, gochara_rules, gocharam_rule_timeline

__all__ = [
    "gocharam_profile",
    "gochara_rules",
    "gocharam_rule_timeline",
    "classical_gochara_status",
    "CLASSICAL_GOCHARA_VEDHA",
    "VEDHA_EXEMPT_PAIRS",
]
