# Vedic Engine VERIFY Flag Audit

**Date:** 2026-08-08
**Status:** Findings Documented (Awaiting Reference Chart for resolution)

## Summary
Per the task brief (Part 1), the Vedic engine has approximately 15 `VERIFY`-flagged conventions. This audit identifies each flag and details the specific input/output pair required from a verified personal reference chart to resolve it. We do not fabricate sources; since these are software-specific conventions or pending a golden reference chart, we leave the `VERIFY` flags in the code untouched until the reference chart is available.

## Audit Findings

### 1. `astrospace/core/vedic/vargas.py`

*   **D5 (Panchamamsha)**: `odd signs → Aries, Aquarius, Sagittarius, Gemini, Libra; even signs → Taurus, Virgo, Pisces, Capricorn, Scorpio. VERIFY.`
    *   **Resolution Criteria**: Check the D5 chart for a known birth. 
    *   **Input**: Longitude of a planet (e.g., Sun in an odd sign at 10°).
    *   **Expected Output**: The D5 sign for that planet matches the JHora convention in the code.
*   **D6 (Shashthamsha)**: `continuous zodiacal count from Aries (each 5°). VERIFY.`
    *   **Resolution Criteria**: Check the D6 chart for a known birth.
    *   **Input**: Longitude of a planet.
    *   **Expected Output**: The D6 sign for that planet matches the continuous count from Aries.
*   **D8 (Ashtamamsha)**: `movable from Aries, fixed from Leo, dual from Sagittarius. VERIFY.`
    *   **Resolution Criteria**: Check the D8 chart for a known birth.
    *   **Input**: Longitude of a planet.
    *   **Expected Output**: The D8 sign for that planet matches this specific mapping.
*   **D11 (Rudramsha)**: `count anti-zodiacally from the 12th of the sign. VERIFY.`
    *   **Resolution Criteria**: Check the D11 chart for a known birth.
    *   **Input**: Longitude of a planet.
    *   **Expected Output**: The D11 sign for that planet matches the anti-zodiacal count.

### 2. `astrospace/core/vedic/constants.py`

*   **Vashya**: `some texts split Sagittarius/Capricorn by half-degrees. (VERIFY)`
    *   **Resolution Criteria**: Find a chart with Moon in the second half of Sagittarius or first half of Capricorn.
    *   **Input**: Moon longitude falling in the disputed half-degrees.
    *   **Expected Output**: The Vashya string output in the reference chart.
*   **Tatwa**: `convention consistent with Horoscope Explorer-style outputs. (VERIFY)`
    *   **Resolution Criteria**: Check the Tatwa in Avkahada Chakra.
    *   **Input**: Moon nakshatra for a known birth.
    *   **Expected Output**: The Tatwa string matches the 5-element cycle starting with Prithvi.
*   **Paya**: `rule family used by common Hindi kundli software. (VERIFY)`
    *   **Resolution Criteria**: Check the Paya (metal of birth foot).
    *   **Input**: Moon house from Lagna (e.g., Moon in the 4th house).
    *   **Expected Output**: The Paya metal matches the reference output (e.g., "Iron" for 4th house).
*   **Vihaga (bird)**: `Pancha-Pakshi convention... (VERIFY)`
    *   **Resolution Criteria**: Check the Vihaga in Avkahada Chakra.
    *   **Input**: Moon nakshatra and paksha (e.g., Shukla paksha).
    *   **Expected Output**: The bird name output in the reference chart.
*   **Functional Benefics/Malefics**: `standard published lists; yogakaraka noted separately. (VERIFY)`
    *   **Resolution Criteria**: Check the list of functional benefics/malefics for a specific Lagna.
    *   **Input**: Lagna sign.
    *   **Expected Output**: The set of benefic and malefic planets matches the code's table.
*   **Numerology**: `convention-dependent; follows common Indian numerology tables. (VERIFY)`
    *   **Resolution Criteria**: Check the numerology good/evil numbers and planet mappings.
    *   **Input**: Birth date (day of the month).
    *   **Expected Output**: The lucky numbers and evil numbers match the chart's numerology section.
*   **Ghatak Chakra**: `month/tithi/day/nakshatra/lagna follow the standard published table... (VERIFY)`
    *   **Resolution Criteria**: Check the Ghatak Chakra section.
    *   **Input**: Janma rashi (Moon sign).
    *   **Expected Output**: The Ghatak month, tithi group, day, nakshatra, and lagna match the code's table.

### 3. `astrospace/core/vedic/avkahada.py`

*   **Sub-nadi per pada**: `simple 3-cycle convention. (VERIFY)`
    *   **Resolution Criteria**: Check the Nadi Pada in Avkahada Chakra.
    *   **Input**: Moon nakshatra pada (1, 2, 3, or 4).
    *   **Expected Output**: The Nadi Pada (Aadi, Madhya, or Antya).

### 4. `astrospace/core/vedic/moontimes.py`

*   **Varjya and Amrit Kalam**: `VERIFY both tables against DrikPanchang before treating as final.` and `upgrading the whole table to "verified" on the strength of a partial match would overclaim, so it stays VERIFY.`
    *   **Resolution Criteria**: Validate the unconfirmed 9 nakshatras for Varjya, and the entire Amrit table.
    *   **Input**: A date where the Moon passes through one of the unconfirmed nakshatras (e.g., Bharani, Rohini).
    *   **Expected Output**: The start ghati matches the reference Panchang output.

### 5. `astrospace/core/vedic/kala.py`

*   **Durmuhurta muhurta numbers**: `day-muhurta numbers (1-based of 15) per vara — VERIFY` and `Tuesday night — VERIFY`
    *   **Resolution Criteria**: Check the Durmuhurta timings for a given weekday and location.
    *   **Input**: A specific date and location (e.g., a Tuesday in Delhi).
    *   **Expected Output**: The calculated Durmuhurta times match the reference chart.

### 6. `astrospace/core/vedic/ghatak.py`

*   **Ghatak of Moon Sign**: `VERIFY all on reference chart.`
    *   **Resolution Criteria**: Same as constants.py Ghatak Chakra verify.

### 7. `astrospace/core/vedic/favourable.py`

*   **Good/evil numbers**: `from the numerology table (VERIFY — convention-dependent)`
*   **Good/evil planets**: `functional benefics/malefics for the lagna (Parashari house-lordship principles, VERIFY).`
    *   **Resolution Criteria**: Covered by constants.py verification requirements.

## Next Steps
Once a golden reference chart with known-correct outputs is provided, we can systematically replace these `VERIFY` flags by asserting the exact outputs in `tests/test_vedic.py` under the "Reference-chart golden tests" section.
