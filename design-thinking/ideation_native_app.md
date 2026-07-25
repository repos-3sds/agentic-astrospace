# Ideation — AstroSpace as a Native iOS/Android App

> A **divergent ideation** pass (design-thinking "ideate" phase): quantity over
> judgment, reimagining AstroSpace as a standard native app. Every cluster is
> anchored to the 7 personas (`persona.md`) and tagged for feasibility against the
> engine (`capabilities.md`). This is a brainstorm to draw from, not a spec.
>
> **Legend:** ✅ engine can do it today · 🔨 new build · 🌙 moonshot

## The reframe

Today AstroSpace is **an astrologer's workbench that believers must navigate** — ~15
data tabs, English-text-only, descriptive not prescriptive. The native app should not
be a smaller workbench.

> **From "a chart you read" → to "a calm guide you ask."**
> The chart becomes the *engine room*, not the front door. The front door is a
> question and a plain answer, with the receipts one tap away.

Three surfaces, one engine, one stable route tree: **Today**, **Ask**, **You (chart)**
— with Guided / Balanced / Practitioner depth riding on top (mode keyed off
term-comfort + "want the why", per `product_brief.md`).

### How-Might-We anchors
- HMW make the *first screen* answer a believer's actual question, not show a
  Sun/Moon/Asc hero?
- HMW turn every plain sentence into a trust-builder *and* a learning hook?
- HMW give people a **next action** ("what to do"), not just a verdict?
- HMW feel native to a Vijayawada homemaker on budget Android *and* a Bengaluru
  practitioner on a Pro Max?

---

## A. The Front Door — "Today" 🌅
*Seed: Overview's "What matters today". Personas: everyone, esp. Lakshmi, Padma, Meera.*

- ✅ A single **daily card**, not a dashboard: one plain verdict, one thing to do, one
  to avoid. Everything else swipes down.
- ✅ **"Today vs Always" as two visual lanes** — daily colour/number/tarabala never
  blended with the birth-constant lucky signature.
- ✅ **Day-quality ring/arc** (Activity-ring style) from tarabala + chandrabala +
  gochara severity — glanceable, per-mode bluntness.
- ✅ **Time-of-day awareness** — surface the *next* auspicious/inauspicious window live
  (Rahu Kalam in 40 min → gentle nudge).
- 🔨 **Morning audio brief** — 30-sec spoken guidance (Telugu/English).
- 🔨 **"Protected" vs "honest" Today** — same data, Lakshmi sees encouragement +
  remedy; Ravi sees the blunt read. Fear-handling as a real toggle.
- 🌙 **Ambient "sky today"** — a living gradient reflecting the actual current sky mood.

## B. Ask — the question-first front door 💬
*The CE was built for this and drives no UI yet. Personas: Lakshmi, Ravi, Meera.*

- 🔨 **Ask is the emotional core.** Type or speak a real question → CE routes to
  domain → computed answer + evidence.
- ✅ **Suggested question chips** seeded from live dasha/gochara.
- 🔨 **Voice-in, voice-out** for low-literacy / elder / commuting users.
- 🔨 **Answer template = Verdict → What to do → Why (tap) → Follow-up.** Never a wall.
- 🔨 **"Ask about a date"** — long-press a calendar day → "what's this good for?"
- ✅ Every answer **footnotes its houses/karakas/yogas/dasha** (CE assembles these).
- 🌙 **Family Ask** — "Is Tuesday good for *my daughter's* engagement?" pulls her chart in.

## C. The "What to do" layer — remedies + muhurta 🪔
*6 of 7 personas want this; 5 of 7 already do remedies. Table stakes, currently absent
— highest leverage.*

- 🔨 **Remedy engine** — gem/mantra/vrat/donation/colour/deity tied to the *specific*
  affliction + dasha + dosha, with provenance ("traditional practice, not a guarantee").
- 🔨 **"Best time to ___" muhurta finder** — pick a goal (sign, travel, buy gold, marry)
  → ranked windows this month, over existing raw windows.
- 🔨 **Remedy tracker / streak** — mantra counter with haptic per tap; a daily-habit loop.
- 🔨 **Shopping-free framing** — never "pay to remove your dosha." Informational, not a
  store CTA (hard constraint).
- ✅ **Manglik / Gandanta / Grahan always paired** with cancellation + remedy + "flag not
  verdict".
- 🌙 **Remedy reminders as gentle rituals** — Live Activity for the day's vrat; lock-screen
  mantra widget.

## D. You / the Chart — depth for Practitioners 📊
*Personas: Anand, plus the believer→learner growth path.*

- ✅ **Collapse-the-plain-layer mode** — straight to Shadbala, Ashtakavarga, 20 vargas,
  Jaimini, 5-level dashas. All already computed.
- ✅ **Provenance panel** — ayanamsha, node type, house system, calc place, confidence.
- ✅ **Chart in 3 styles (S/N/E)** with native pinch-zoom + tap-a-planet detail.
- 🔨 **"Why this reading?" everywhere** — plain_why/technical_why already exist; make the
  reveal a signature interaction.
- 🔨 **Learning layer** — tap a yoga → classical rule + verse + worked example.
- 🌙 **Chart time-scrubber** — drag a timeline; watch dashas + transits animate over a life.

## E. Matchmaking — the high-value event 💍
*Personas: Suresh, Meera. Highest per-event spend in the market.*

- ✅ **Gun Milan as a guided story**, not a table: score → the 2 things that matter →
  dosha check → remedy → suggested muhurtham (over the existing 36-point engine).
- 🔨 **Shareable match report (PDF/story card)** to forward on WhatsApp.
- 🔨 **"Add the prospect"** lightweight birth-detail flow (no full profile).
- 🌙 **Two-family shared view** — both sides see the same honest, non-fear report.

## F. Festival / observance calendar + habit loop 📅
*Personas: Padma, Lakshmi, Meera. Retention hook.*

- 🔨 **Personalized "what to observe & when"** — *your* vrats/festivals with prep reminders.
- ✅ **Panchanga is already complete** — render it as a calm monthly rhythm, not a dump.
- 🔨 **Festival countdown widgets + notifications** ("Varalakshmi Vratam in 3 days").
- 🌙 **Family observance sync** — Meera abroad and Padma in Guntur, timezone-correct each.

## G. Language, audio, reach 🗣️
*Functional requirement, not polish — the core is Telugu-first. Personas: Lakshmi,
Padma, Meera.*

- 🔨 **Telugu content + mixed-script** end to end, not a token toggle.
- 🔨 **Audio-render every daily guidance** (warm register per mode).
- ✅→🔨 **Large-tap, low-connectivity mode** — big fonts, taps over swipes, offline-cached
  daily card for budget Android + weak networks.
- 🔨 **Standard a11y** — WCAG AA, screen-reader labels on chart glyphs, 200% zoom,
  reduced motion, 44px targets.

## H. Trust, honesty & the "why" 🔬
*The brand: "computed, not conjured." Converts Ravi.*

- ✅ **Visible "Computed" badge** with the calculation trail — the anti-Co-Star signal.
- ✅ **Convention-dependent items labelled as tradition** vs. deterministic fact.
- 🔨 **"Show your work" as trust *and* growth loop** — tap why → learn a term → drift
  toward Practitioner.
- ✅ **Never predict death/longevity; refer out** on health/legal/money — guardrails as
  first-class empty states, not error messages.

## I. Native platform superpowers 📱
*What makes it a real native app, not a web wrapper.*

- 🔨 **Home- & lock-screen widgets** — day-quality ring, next window, tithi/nakshatra,
  remedy-of-the-day.
- 🔨 **Live Activities / Dynamic Island** — Rahu Kalam countdown, muhurta window, vrat timer.
- 🔨 **watchOS / Wear complication** — glanceable day quality + next window.
- 🔨 **Siri / Google Assistant** — "is now a good time?" / "when's Rahu Kalam today?"
- 🔨 **Smart notifications** — morning "your day"; time-sensitive window alerts (opt-in,
  never fear-spam).
- 🔨 **Share sheet → story cards** — daily guidance, match report, "why this reading".
- 🔨 **Offline-first daily card** — engine is Moshier (no data files), so on-device/cached
  is feasible.
- 🔨 **Haptics as ritual** — soft tap per mantra; distinct haptic entering/leaving a window.
- 🌙 **App Clip / Instant App** — scan a QR at a temple → instant panchang, no install.

## J. Human connection / handoff 🤝
*Every believer persona ultimately pays for a human; not built yet.*

- 🔨 **"Talk to an astrologer" handoff** pre-loaded with the computed chart + the exact
  question — the human starts informed (differentiator vs. cold marketplace).
- 🔨 **Save/share a reading with your family astrologer** — meet them where they are.
- 🌙 **Verified-practitioner layer** — practitioners as supply, believers as demand,
  computed rigor as the shared language.

## K. Onboarding & mode capture 🚪
- 🔨 **Mode captured in 2 questions, invisibly** — term-comfort + "want the why?" → mode.
  No astrology quiz.
- ✅ **City autocomplete** already covers all AP+TS villages + world cities.
- 🔨 **Mode as a comfort dial** in settings, changeable anytime — not a locked identity.
- 🔨 **Progressive profiling** — don't demand exact birth time upfront; degrade gracefully
  + flag confidence.

## L. Monetization ideas 💰
*Maps cleanly to modes.*

- 🔨 **Practitioner Pro** (Anand, ₹300–1000) — full tools, learning layer, exports, provenance.
- 🔨 **Remedy/timing/matchmaking as events** (Suresh, Meera) — pay per match report, per
  muhurta run, per audio consult.
- 🔨 **Diaspora tier** (Meera, higher $) — timezone-correct panchang + family sync + festival prep.
- 🔨 **Trust-gated upsell** (Ravi) — free until the "why" earns belief; never fear-gated.

## M. Moonshots 🌙
- **AR sky** — point your phone up, see *your* transiting planets over the real sky.
- **"Life weather forecast"** — a 12-month dasha/transit outlook rendered like a calm,
  honest weather app.
- **Couple/family shared timing** — a muhurtham good across *multiple* charts.
- **On-device private AI** — the chart never leaves the phone; the CE answers locally.

---

## Light convergence — if only a few ship

| Rank | Idea | Why it wins | Effort |
|---|---|---|---|
| 1 | **"What to do" layer (remedies + goal muhurta)** | #1 shared gap; table stakes for 6/7; descriptive→prescriptive leap | 🔨🔨 High (new engine) |
| 2 | **Ask front door (CE-wired)** | Matches the believer's mental model; engine's already built for it | 🔨 Medium |
| 3 | **Today card + widgets + morning notification** | Daily-habit / retention loop; ✅ data mostly exists | 🔨 Medium |
| 4 | **Telugu + audio** | Unlocks the actual core audience; reach blocker today | 🔨🔨 High (content) |
| 5 | **"Why this reading" everywhere** | Cheap-ish; it's the brand *and* the growth loop | ✅→🔨 Low-Med |

**The product bet (one line):** *keep the computed rigor, but bury the workbench and lead
with a question, a plain answer, a thing to do, and the receipts — natively, in the
user's language.*
