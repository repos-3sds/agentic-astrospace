"""Abhijit — the intercalary 28th nakshatra, as an *overlay* on the standard 27.

Abhijit is NOT a 28th entry in the nakshatra sequence. It is a separate arc
drawn on top of Uttara Ashadha and Shravana, both of which keep their full
13°20' spans. A Moon inside the Abhijit arc still has Uttara Ashadha or
Shravana as its birth nakshatra — never Abhijit. This is why `nakshatra_of()`
is deliberately untouched by this module, and why nothing here feeds
Vimshottari dasha, Ashtakoota compatibility, or any other consumer of the
standard 27: those systems all use the 27 and are unaffected.

Span, cross-checked 2026-08-10 against four independent sources (Wikipedia,
vedicmarga.com, psychologicallyastrology.com, and search-level agreement from
several others), all giving 6°40' to 10°53'20" of Capricorn:

    276°40'00"  to  280°53'20"   (width 4°13'20")

Both boundaries were additionally re-derived against this engine's own
nakshatra math and match to floating-point precision — see
tests/test_bphs_ground_truth.py's TestAbhijitNakshatra:

  - the start is exactly Uttara Ashadha's 4th pada boundary
    (20 x 13°20' + 3 x 3°20' = 276°40')
  - the end is exactly the first 1/15th of Shravana
    (21 x 13°20' + 13°20'/15 = 280°53'20")

That exact reproduction is the reason the span itself is treated as solid
rather than merely plausible. `source_status` stays "convention_dependent"
for a different reason: traditions genuinely disagree on whether to use
Abhijit *at all*, not on where it sits. The classical 27-nakshatra
standardisation (Surya Siddhanta onward) drops it, since 360°/28 gives no
clean division; the older 28-nakshatra enumerations (Taittiriya Brahmana)
keep it. Its surviving practical use is muhurta — electional timing — not
natal chart reading.

Deity: Brahma / Parabrahma (distinct from Brahma-dev/Prajapati, who rules
Rohini).

Deliberately NOT implemented here, for lack of a verified source rather
than lack of interest:

  - any goal-preference scoring (which undertakings Abhijit favours). No
    source found gives a checkable mapping, and muhurta.py's GOALS table
    is not going to be seeded with a guess — the same standard applied to
    the D-60 deity list before it shipped.
  - Ashtottari and Shastihayani dasha, the two dasha systems that do use
    Abhijit. Neither is implemented in this codebase at all; if either is
    built later, this module is the piece it should read from.
"""

# Arc boundaries in sidereal degrees. Written as explicit DMS arithmetic
# rather than decimal literals so the classical figures stay readable and
# the derivation above is checkable line by line.
ABHIJIT_START = 276.0 + 40.0 / 60.0                    # 276°40'00"
ABHIJIT_END = 280.0 + 53.0 / 60.0 + 20.0 / 3600.0      # 280°53'20"

DEITY = "Brahma (Parabrahma)"


def in_abhijit_arc(lon: float) -> bool:
    """True when a sidereal longitude falls inside the Abhijit arc.

    Half-open on the upper bound, matching how every other boundary in this
    engine buckets (`nakshatra_of`, `_parts` in vargas.py): a longitude
    exactly at the end belongs to what follows, not to Abhijit.
    """
    return ABHIJIT_START <= (lon % 360.0) < ABHIJIT_END


def abhijit_status(lon: float) -> dict:
    """Descriptive Abhijit overlay for a sidereal longitude.

    Always returns the same shape; `active` carries whether the longitude is
    actually in the arc. Purely descriptive — this never renames or overrides
    the standard nakshatra, which stays whatever `nakshatra_of()` says.
    """
    return {
        "active": in_abhijit_arc(lon),
        "name": "Abhijit",
        "deity": DEITY,
        "span_start": ABHIJIT_START,
        "span_end": ABHIJIT_END,
        "overlaps": "Uttara Ashadha's 4th pada and Shravana's first 1/15th",
        "source_status": "convention_dependent",
        "rule": (
            "Abhijit is an intercalary arc laid over the standard 27 "
            "nakshatras, not a 28th nakshatra in sequence: Uttara Ashadha "
            "and Shravana keep their full spans, and a Moon here still takes "
            "one of those two as its birth nakshatra, never Abhijit. Retained "
            "mainly for muhurta; not used by Vimshottari dasha or Ashtakoota "
            "compatibility, both of which use the standard 27."
        ),
    }
