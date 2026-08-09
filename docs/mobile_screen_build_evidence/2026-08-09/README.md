# Mobile Screen Build Evidence — 2026-08-09

Viewport: 375x812 browser preview against `npm run build:dev`.

Fixture: Playwright intercepted `/api/v1/kundlis` and
`/api/v1/ask/threads/fixture-thread` with one structured Ask response. This
keeps all three screenshots on the same backend payload so the visible
differences are persona-template differences only.

## Ask Answer Persona Templates

- `ask-answer-guided-375x812.png` — Figma `212:971`, Guided
- `ask-answer-balanced-375x812.png` — Figma `212:1019`, Balanced
- `ask-answer-practitioner-375x812.png` — Figma `212:1077`, Practitioner

Verification:

- `cd ui && npm run build:dev`
- Playwright 375x812 screenshot pass for Guided, Balanced, Practitioner
- No browser console errors during the final screenshot pass
