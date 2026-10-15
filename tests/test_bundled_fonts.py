"""The bundled web fonts hold the face their filename and @font-face claim.

On 2026-10-15 the two Playfair Display files were swapped when they were
first bundled, so every heading in the native app rendered italic while
the CSS asked for the upright face. A font file's name does not prove its
contents; its name table does.
"""
from pathlib import Path

import pytest
from fontTools.ttLib import TTFont

FONTS = Path(__file__).resolve().parent.parent / "ui" / "public" / "fonts"

EXPECTED = {
    "inter-latin.woff2": ("Inter", False),
    "playfair-display-latin.woff2": ("Playfair Display", False),
    "playfair-display-latin-italic.woff2": ("Playfair Display", True),
}


@pytest.mark.parametrize("filename,expected", EXPECTED.items(), ids=list(EXPECTED))
def test_bundled_font_matches_its_declared_face(filename, expected):
    family, italic = expected
    font = TTFont(FONTS / filename)
    assert font["name"].getDebugName(1) == family
    assert bool(font["OS/2"].fsSelection & 1) is italic, (
        f"{filename} is {'italic' if not italic else 'upright'}; "
        "styles.scss declares the opposite"
    )
    assert (font["post"].italicAngle != 0) is italic
    assert "fvar" in font and {a.axisTag for a in font["fvar"].axes} == {"wght"}
