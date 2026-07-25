# Design Principles & Constraints — AstroSpace

> The non-negotiables and the house style. A design-thinking agent should treat
> Section 4 (safety) as hard constraints, not preferences.

## 1. Voice & trust

- **Computed, not conjured.** The brand is *"Vedic astrology, computed."* Never
  fabricate a reading; everything traces to a calculation. Where a convention is
  disputed, say so (the engine already flags `convention_dependent` / `VERIFY`).
- **Show your work, on demand.** Every plain statement should have a *"Why this
  reading?"* that reveals the computed evidence (the engine already produces
  `plain_why` + `technical_why`, provenance, and rule sources). This is both a trust
  device and the believer→learner growth path.
- **Grounded reassurance, not flattery or fear.** Warm and practical, never
  "everything is amazing," never doom. Fear-and-upsell is the anti-pattern users
  explicitly distrust (see persona survey).

## 2. Progressive disclosure

- **Plain on top, depth underneath.** Guided users see the answer; one tap reveals
  the chart evidence. Practitioners can collapse the plain layer and go straight to
  tools. Same route, adaptive depth — never a second app.
- **Separate "Today" (changes daily) from "Always" (birth-constant).** Don't blend
  daily colour/number/tarabala with the birth-constant lucky signature.

## 3. Adaptive by experience mode (not belief)

- Mode is keyed off **term-comfort + "want the why"**, captured at onboarding.
- Mode should drive: **labels** (Dashas ↔ "Life Periods"), **nav priority**, **default
  disclosure state**, **copy register**, and ideally the **reading text** itself.
- Route tree stays **stable**; only labels/priority/disclosure adapt. A Guided user
  deep-linking to a Practitioner route must still land there cleanly.

## 4. Safety & ethics (HARD constraints)

- **No death or longevity predictions.** The engine deliberately excludes ayurdaya
  output; the product must never predict death timing.
- **Not medical, legal, financial, or emergency advice.** For health/legal/money
  distress, **refer out** ("consult a doctor / lawyer / advisor"), don't adjudicate.
- **Litigation/disputes: advisory tone only** — no deterministic "you will win/lose."
- **Fear-handling is a per-mode setting.** Some personas (Lakshmi, Padma, Suresh,
  Meera) must **not** be told bluntly about health/death/children/marriage-failure;
  others (Ravi, Anand) want full honesty. The *same* dosha needs two deliveries. Never
  ship a single global bluntness.
- **No manipulation.** Never "pay to remove your dosha." Remedies are traditional
  practice offered helpfully, never as fear leverage.
- **Sensitive topics (marriage compatibility, doshas):** always pair a caution with a
  cancellation/remedy and a "this is a flag, not a verdict" framing.

## 5. Accessibility & reach

- **Language:** Telugu is a functional requirement for the core audience, not polish;
  English is today's default. Design for multi-language content and mixed-script.
- **Audio:** the low-tech / elder / commuting personas want to *listen*. Design daily
  guidance to be audio-renderable.
- **Large, tap-first, low-connectivity friendly** for elder/rural users (Padma):
  large fonts, taps over swipes, works on budget Android and weak networks.
- **Standard a11y:** WCAG AA contrast, keyboard/screen-reader, 200% zoom, reduced
  motion, 44px touch targets (already partly covered in the mobile plan).

## 6. Data honesty

- **Provenance visible** for the Practitioner (ayanamsha, node type, house system,
  calculation place, confidence flags — the engine emits all of this).
- **Personal vs. universal** clearly distinguished (e.g., "number of the day" is
  universal; "your lucky number" is personal).
- **Convention-dependent numerology/remedies** should be labelled as tradition, not
  presented as deterministic fact.

## 7. Anti-patterns (do not do)

- One UI at one depth that forces believers to navigate an astrologer's workbench.
- Jargon on the Guided surface; dumbed-down mush on the Practitioner surface.
- Global "gentle" or global "blunt" tone.
- Descriptive-only ("your day is mixed") with no prescriptive next step.
- Horizontal page scroll; dense desktop tables shrunk onto phones.
