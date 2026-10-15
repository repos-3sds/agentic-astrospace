Status: canonical — what these files are and how to refresh them.

Latin subsets of the variable Google Fonts builds, bundled so the app never
waits on, or leaks a request to, fonts.googleapis.com:

| File | Family | Axes |
| --- | --- | --- |
| `inter-latin.woff2` | Inter | wght 400–700 |
| `playfair-display-latin.woff2` | Playfair Display, upright | wght 400–900 |
| `playfair-display-latin-italic.woff2` | Playfair Display italic | wght 400–900 |

Both families are OFL-licensed. `@font-face` rules live in `src/styles.scss`.
To refresh, request the CSS from Google Fonts with a modern browser user agent
and download the `U+0000-00FF` (latin) file for each face.

A filename proves nothing about the face inside; the two Playfair files
shipped swapped once (2026-10-15) and every heading went italic.
`tests/test_bundled_fonts.py` reads each file's name table and fails the
backend suite if a file does not hold the face `styles.scss` declares for it.
