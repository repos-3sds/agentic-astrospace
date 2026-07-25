# Product Brief — AstroSpace

> Distilled from the build sessions (engineering + product survey). Reconcile the
> positioning section against `VISION.md` / `README.md` when available — those are
> the canonical vision statements; this brief may phrase things differently.

## 1. What AstroSpace is

A **computed Vedic astrology** product. The differentiator is in the tagline the
app already uses: *"Vedic astrology, computed"* / *"Understand your chart. Know your
timing."* Every reading is derived from a real, auditable calculation engine
(Swiss Ephemeris, classical rules with provenance) — not hand-wavy generic
horoscopes. Trust through rigor is the brand.

## 2. Who it's for

**Primary market:** India, with a **Telugu-belt (Andhra/Telangana) core**, plus the
**Indian diaspora**. See `persona.md` for the seven personas. The critical finding:

- The audience is **not** blank-slate Western horoscope readers. They live inside an
  existing folk-astrology world — family astrologer, WhatsApp panchang, temple,
  muhurtham, matchmaking, rahu kalam, remedies.
- The audience splits on **complexity-appetite, not belief**. Deep believers sit at
  both extremes (want-it-simple vs. want-full-detail). Belief level does not predict
  what UI they need.

## 3. The strategic decision: two experiences, one engine

Capture **experience intent** up front and let it drive information architecture,
copy, and depth — over a **single stable route tree** (adaptive labels/priority, not
a fork). Three modes, default **Balanced**:

| Mode | For | Promise | Keyed off |
|---|---|---|---|
| **Guided** | Believers / followers | "Tell me what this means and what to do" | low term-comfort + "just tell me" |
| **Balanced** *(default)* | Most people | Plain first, the "why" one tap away | middle |
| **Practitioner** | Astrologers / enthusiasts / learners | "Give me the tools and calculations" | high term-comfort + "want full detail" |

Design the two poles (Guided, Practitioner); **Balanced = Guided content + Practitioner access** (a derived config, not a third design). The bridge — a *"Why this reading?"* affordance on every plain statement — is also the growth loop (believer → learner).

## 4. What we're missing (the product gaps)

The engine is superb at **describing the sky**; the users want it to be
**prescriptive and personal**. Ordered by leverage:

1. **The "what to do" layer** — *remedies (gem/mantra/vrat/donation/colour tied to the affliction)* and *goal-based muhurta ("best time to sign/travel/marry")*. 6 of 7 personas want this; 5 of 7 already perform remedies. **Table stakes, currently absent.**
2. **Question-first "Ask" surface** — the believer's mental model is a question. The Context Engine was built exactly for this (question → domain → computed context) but drives no UI yet.
3. **Language + audio** — Telugu content and audio delivery for the Guided core; the app is English-text-only today.
4. **Festival / vrat / observance calendar** — the daily-habit + retention hook.
5. **Timezone/geo correctness** — panchang/muhurtham default to birth place; breaks for the diaspora segment.
6. **Fear-handling as a mode setting** — same affliction needs a gentle vs. honest delivery depending on persona.

## 5. Positioning vs. the market

- **Co-Star / Sanctuary (Western pop-astro):** identity/aesthetic, shallow calc. We are deeper and Vedic; we do **not** natively serve the Gen-Z pop-astro persona (Ananya) — a deliberate scoping call, not an accident.
- **AstroSage / Astrotalk / Ganesha (Indian):** broad, but often generic, fear/upsell-driven, and astrologer-marketplace-first. Our wedge is **computed rigor + honest, non-fear framing + a genuinely adaptive believer/practitioner split**.

## 6. Monetization hypothesis (validate)

- **Practitioner** pays for **depth/tools/learning** (highest per-user).
- **Believers** pay for **remedies, timing, matchmaking, human connection** — events, not raw charts.
- **Skeptics** pay only **after trust is earned** (the "why" layer).
- **Casual/social** barely pays — value is reach, not revenue.
- Matchmaking is the classic high-spend Indian event; diaspora has higher $ willingness.

## 7. Open decisions for design

1. Does `experienceMode` change the **reading text itself** (backend/CE), or only presentation? (Recommendation: backend too — else Guided is just Practitioner with smaller words.)
2. Is the **remedy/muhurta content layer** in-scope alongside experience modes, or a fast-follow? (If fast-follow, the first Guided release is *descriptive-plain*, not yet prescriptive — state it.)
3. **Ananya (Gen-Z pop-astro):** target segment or funnel-we-don't-chase-yet?
4. How blunt is the day-quality verdict allowed to be, per mode?
