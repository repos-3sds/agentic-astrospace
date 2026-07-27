"""Kakshya calculations for Gocharam."""

from __future__ import annotations

# The 8 Kakshyas of a sign (each 3.75 degrees), ordered slowest to fastest.
KAKSHYA_LORDS = (
    "Saturn",
    "Jupiter",
    "Mars",
    "Sun",
    "Venus",
    "Mercury",
    "Moon",
    "Lagna",
)

def kakshya_of(degree_in_sign: float) -> dict:
    """Returns the Kakshya lord and index for a given degree in a sign."""
    # Ensure degree is within [0, 30)
    degree = degree_in_sign % 30.0
    
    # Each Kakshya is 3.75 degrees
    index = int(degree // 3.75)
    
    # Failsafe in case of floating point edge cases
    if index >= 8:
        index = 7
        
    lord = KAKSHYA_LORDS[index]
    
    return {
        "index": index,
        "lord": lord,
        "start_degree": index * 3.75,
        "end_degree": (index + 1) * 3.75,
    }
