from __future__ import annotations

import hashlib
import math
import re

_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9_-]{1,}")


class FeatureHashEmbedder:
    """Dependency-free lexical vector used until a semantic provider is configured."""

    dimensions = 384
    provider = "feature-hash-v1"

    def embed(self, text: str) -> tuple[float, ...]:
        vector = [0.0] * self.dimensions
        for token in _TOKEN_RE.findall(text.lower()):
            digest = hashlib.blake2b(token.encode(), digest_size=8).digest()
            value = int.from_bytes(digest, "big")
            index = value % self.dimensions
            vector[index] += -1.0 if value & 1 else 1.0
        norm = math.sqrt(sum(value * value for value in vector))
        if not norm:
            # No hashable token in the text. Devanagari-only passages land here
            # (the token pattern requires a Latin first character), as does
            # table debris containing no words at all.
            #
            # The zero vector is returned because the column is a fixed-width
            # vector and there is nothing better to store — but it is not a
            # point in the space. Callers must test `is_degenerate` rather than
            # assume a usable embedding came back; see the note there.
            return tuple(vector)
        return tuple(value / norm for value in vector)


def is_degenerate(vector: tuple[float, ...]) -> bool:
    """True when an embedding carries no signal at all.

    This matters more than it looks. Cosine similarity against a zero-magnitude
    vector is undefined, so pgvector returns NaN — and Postgres orders NaN above
    every real value. A handful of such rows will therefore occupy the top of
    every ranked search until something filters them out.
    """
    return not any(vector)
