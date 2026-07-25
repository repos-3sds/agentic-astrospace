# AstroSpace — User Personas

## About this document

Seven personas covering AstroSpace's realistic audience (India-centric, Telugu-belt
core, plus diaspora). Each follows a standard UX persona template: snapshot →
bio → goals → needs → frustrations → motivations → behaviours → astrology profile
→ attitude dials → the completed discovery survey → design implications.

> **⚠️ These are synthetic proto-personas — a design thinking tool, not real
> research data.** They were built to surface patterns quickly. Validate and
> replace the sharp/surprising claims with real survey responses (see
> `docs/astrology_survey.md`) before committing product decisions.

**The load-bearing insight across all seven:** the axis that should drive the
app's experience mode is **term-comfort + "do I want the why"** — *not* belief
level. Deep believers land on both extremes (Lakshmi wants it dead simple; Anand
wants full technical). Skeptics and devout elders can both want it simple.
Belief is a red herring for IA; complexity-appetite is the real signal.

**Experience-mode legend:** `Guided` (plain, reassurance-first, chart hidden) ·
`Balanced` (plain-first, "why" one tap away) · `Practitioner` (technical, tools-first).

---

## Summary matrix

| # | Persona | Mode | Who / where | Core use case | Belief | Term comfort | Wants | Format | Pays for |
|---|---|---|---|---|---|---|---|---|---|
| P1 | **Lakshmi** | Guided | 34, homemaker, Vijayawada | Kids, health, muhurtham | 5/5 | 2/5 | Just tell me | Audio, cards, Telugu | Remedies, human, timing |
| P2 | **Ravi** | Balanced | 28, IT, Hyderabad | Job & relationship decisions | 3/5 | 2/5 | What **+ why** | Text, on-demand | Daily guidance (if trust earned) |
| P3 | **Padma** | Guided | 58, retired teacher, Guntur | Festivals, family, puja | 5/5 | 3/5 | Just tell me | Text (large), audio, Telugu | Human astrologer, remedies |
| P4 | **Anand** | Practitioner | 41, business owner, Bengaluru | Business timing, self-study | 4/5 | 5/5 | Full technical | Detailed text | Depth, tools, learning |
| P5 | **Suresh** | Balanced | 52, salaried, Rajahmundry | Daughter's matchmaking, dosha | 4/5 | 3/5 | What + why | Reports, text | Match reports, human, muhurtham |
| P6 | **Ananya** | Guided | 23, junior designer, Bengaluru | Identity, love vibes, fun | 2/5 | 2/5 | Just tell me (light) | Story cards, visual | Little/nothing (freemium) |
| P7 | **Meera** | Balanced | 38, NRI professional, USA | Festivals/muhurtham abroad, kids, parents | 4/5 | 3/5 | What + why | Text, audio | Timing, human, daily (higher $) |

---

## P1. Lakshmi — "The Devoted Homemaker"

> "Just tell me clearly what to do — in Telugu — and please don't frighten me."

**Experience mode:** Guided · **Segment:** Believer core, family decision-maker

### Snapshot
| | |
|---|---|
| Age | 34 |
| Location | Vijayawada (Tier-2 city) |
| Occupation | Homemaker |
| Family | Married, two school-age children |
| Languages | Telugu (primary), some English |
| Tech comfort | Low–moderate (WhatsApp, YouTube, phone-first) |
| Devices | Budget Android phone |
| Belief (1–5) | 5 |
| Term comfort (1–5) | 2 |

### Bio
Runs the household and is the family's "astrology gatekeeper." Consults the family
astrologer for anything important and forwards daily panchang/rashi messages on
WhatsApp. Astrology is woven into daily life — festivals, fasts, naming, timings —
not a separate hobby.

### Goals
- Keep her children's education and future on a safe, blessed track.
- Pick auspicious times (muhurtham) for family events.
- Stay reassured that the family is protected.

### Needs
- Plain-language guidance she can act on today.
- Remedies she can actually perform (puja, fast, donation, colour).
- Telugu, and ideally audio she can listen to while working.

### Frustrations
- Astrologers/apps use jargon she can't follow.
- Fear-based readings that leave her anxious.
- English-only apps.

### Motivations
- Protecting and advancing her children.
- Doing the "right" traditional thing at the right time.

### Behaviours & context
- Checks **daily** (morning panchang) and before any family event.
- Turns to it when worried; leaves feeling **reassured**.
- Performs remedies **regularly**; trusts a **human astrologer** for big matters.

### Astrology profile
- **Checks:** children, health, marriage/family, muhurtham, daily timings.
- **Wants:** *what to do* — not the why.
- **Remedies:** does them regularly; expects the app to prescribe.
- **Fear-handling:** protect me — never blunt about health/death/kids/marriage.
- **Human vs app:** human for serious things; app for daily reassurance.
- **Actions wanted:** daily guidance, remedies, muhurtham, save/share with family.

### Attitude dials
- Belief: 5/5 · Simple↔Technical: **Simple** · Reassurance↔Honesty: **Reassurance** · Casual↔Committed: **Committed** · Routine↔Decision: **Routine**

### Completed survey
- **1–5:** 25–34 · Female · Tier-2 city · Homemaker · Telugu
- **6–8:** Influence 5 · Vedic jyotish · via family astrologer, WhatsApp, temple, panchang
- **9–11:** Checks daily · triggers: habit/decisions/worry/events · feels **reassured**
- **12–15:** Areas — Children, Health, Marriage (top: **Children**) · Muhurtham 5 · daily timings **daily**
- **16–18:** Short paragraph · audio + story cards · **morning**
- **19–21:** Term comfort 2 · wants **"just tell me what"** · learn a little
- **22–25:** Hard period → remedies, reassurance, do's/don'ts, timing · does remedies **regularly** · timing value 5 · prefers **human**
- **26–29:** Trusts specificity/referral/reputation · distrusts fear + money-to-remove · frightened **often** · don't tell bluntly: health/death/kids/marriage
- **30–32:** Pays for **big events** · would pay for remedies/human/timing · **<₹100/mo**
- **33:** *"Will my son do well in studies and get settled?"*
- **34:** *"They use difficult words and frighten us. Tell me clearly what to do, in Telugu, and don't scare me."*

### What this means for AstroSpace
The purest Guided user. Needs Telugu + audio + remedies + gentle framing — three of
which the app doesn't have yet. If the Guided track can't speak Telugu and prescribe
remedies, it doesn't serve its own core persona.

---

## P2. Ravi — "The Pragmatic Skeptic"

> "Cut the fear and the gemstone upselling. Show me *why*, and I'll decide if I believe it."

**Experience mode:** Balanced · **Segment:** Semi-believer, decision-triggered

### Snapshot
| | |
|---|---|
| Age | 28 |
| Location | Hyderabad (metro) |
| Occupation | Software engineer |
| Family | Single, lives with roommates |
| Languages | English (primary), Telugu |
| Tech comfort | High |
| Devices | Flagship phone, laptop |
| Belief (1–5) | 3 |
| Term comfort (1–5) | 2 |

### Bio
Grew up around astrology but treats it as one input, not gospel. Opens an app or
Googles when a real decision or anxiety hits — a job offer, a relationship crossroads.
Allergic to fear-mongering and "pay to remove your dosha" tactics.

### Goals
- Make better calls on career and relationships.
- Get a second, structured perspective he can reason about.

### Needs
- The *why* behind any claim, so he can judge its credibility.
- Zero fear-baiting, zero upsell.
- On-demand, not daily nagging.

### Frustrations
- Vague, one-size-fits-all horoscopes.
- Fear-based or salesy readings.
- No reasoning shown → can't trust it.

### Motivations
- Reducing uncertainty on big decisions.
- Intellectual curiosity ("does this actually track?").

### Behaviours & context
- Checks **only before big decisions**; leaves feeling **informed**.
- Prefers a **mix** of app + own judgment; rarely does remedies.

### Astrology profile
- **Checks:** career/job, relationships, money.
- **Wants:** *what + why* — the reasoning is the trust-builder.
- **Remedies:** once or twice; skeptical.
- **Fear-handling:** **full honesty** — don't sugarcoat.
- **Human vs app:** mix; self-directs.
- **Actions wanted:** ask a specific question, see the reasoning, timing.

### Attitude dials
- Belief: 3/5 · Simple↔Technical: **Simple-but-reasoned** · Reassurance↔Honesty: **Honesty** · Casual↔Committed: **Casual** · Routine↔Decision: **Decision**

### Completed survey
- **1–5:** 25–34 · Male · Metro · Salaried professional · English
- **6–8:** Influence 3 · Vedic + sun-sign (casual) · via app, social, WhatsApp
- **9–11:** Checks **only at big decisions** · triggers: decisions/worry/curiosity · feels **informed**
- **12–15:** Areas — Career, Relationships, Money (top: **Career**) · Muhurtham 3 · daily timings only for important tasks
- **16–18:** Short paragraph · text · **only when I ask**
- **19–21:** Term comfort 2 · wants **"what + why"** · learn a little
- **22–25:** Hard period → explanation, do's/don'ts, timing · remedies once/twice · timing value 3 · prefers **mix**
- **26–29:** Trusts **reasoning + proper calculations + track record** · distrusts vague/fear/money/pushy · frightened once/twice · **full honesty**
- **30–32:** Pays **never** (yet) · would pay for daily guidance/detailed reading · **₹100–300/mo**
- **33:** *"Should I switch jobs now or wait — and is this relationship going anywhere?"*
- **34:** *"Show me why you're saying something so I can decide if I believe it."*

### What this means for AstroSpace
The "why one tap away" bridge exists *for Ravi*. He's the proof that the
Practitioner-grade evidence layer (already in `technical_why`) isn't just for
astrologers — it's what converts a skeptic. Trust-first, then he'll pay.

---

## P3. Padma — "The Devout Elder"

> "Make it simple, in Telugu, with big letters. Tell me the festivals, the good days, and the puja."

**Experience mode:** Guided · **Segment:** Devout, ritual/calendar-driven

### Snapshot
| | |
|---|---|
| Age | 58 |
| Location | Guntur (Tier-2 city) |
| Occupation | Retired schoolteacher |
| Family | Married, grown children, grandchildren |
| Languages | Telugu |
| Tech comfort | Very low (large fonts, taps not swipes) |
| Devices | Hand-me-down Android, small screen |
| Belief (1–5) | 5 |
| Term comfort (1–5) | 3 (knows tithi/nakshatra/rahu kalam; not chart jargon) |

### Bio
Structures each day and year around panchang, festivals, vrat and temple. Deeply
devout; astrology is inseparable from religious practice. Wary of anything that
feels commercial or manipulative.

### Goals
- Observe the right festivals, fasts and pujas on the right days.
- Wellbeing of children and grandchildren.

### Needs
- Dead-simple, large, Telugu content.
- A personalised festival/vrat/observance calendar.
- Reassurance rooted in tradition.

### Frustrations
- Small text, English, swipe-heavy interfaces.
- Anything that feels like a sales pitch.

### Motivations
- Devotion and tradition.
- Family's protection and blessings.

### Behaviours & context
- Checks **daily** (panchang, festivals); performs remedies **regularly**.
- Trusts the **temple priest / human astrologer** above any app.

### Astrology profile
- **Checks:** festivals/observances, family, health, spirituality, muhurtham.
- **Wants:** *what to do*; no interest in learning the mechanics.
- **Remedies:** central to her practice.
- **Fear-handling:** gentle — no blunt death/health/children talk.
- **Human vs app:** strongly human/temple.
- **Actions wanted:** daily observance, festival reminders, remedies, audio.

### Attitude dials
- Belief: 5/5 · Simple↔Technical: **Simple** · Reassurance↔Honesty: **Reassurance** · Casual↔Committed: **Committed** · Routine↔Decision: **Routine**

### Completed survey
- **1–5:** 55+ · Female · Tier-2 city · Retired · Telugu
- **6–8:** Influence 5 · Vedic jyotish · via temple/priest, panchang, family astrologer, newspaper
- **9–11:** Checks **daily** · triggers: habit + festival dates · feels **reassured**
- **12–15:** Areas — Family, Health, Spirituality (top: **Family**) · Muhurtham 5 · daily timings **daily**
- **16–18:** Short paragraph · text (large) + audio · **morning**
- **19–21:** Term comfort 3 · wants **"just tell me what"** · **keep it simple**
- **22–25:** Hard period → reassurance, remedies, do's/don'ts · remedies **regularly** · timing value 5 · prefers **human**
- **26–29:** Trusts referral/reputation/specificity · distrusts money-to-remove + pushy · frightened once/twice · don't tell bluntly: death/health/kids
- **30–32:** Pays **occasionally** (priest/astrologer) · would pay for human/remedies · **nothing/mo to apps**
- **33:** *"Are my children and grandchildren safe and well?"*
- **34:** *"Simple, Telugu, big letters — festivals, good days, and what puja to do."*

### What this means for AstroSpace
Accessibility (font size, Telugu, audio, tap-first) is a *functional requirement*
for her, not polish. Her value is retention via the festival/observance calendar —
a feature the app doesn't surface yet. She won't pay apps, but she's the daily-habit
anchor of a family account.

---

## P4. Anand — "The Enthusiast-Practitioner"

> "Most apps are shallow and generic. Give me the real calculations and let me inspect them."

**Experience mode:** Practitioner · **Segment:** Learner/prosumer

### Snapshot
| | |
|---|---|
| Age | 41 |
| Location | Bengaluru (metro) |
| Occupation | Small-business owner |
| Family | Married, one child |
| Languages | English, Kannada |
| Tech comfort | High |
| Devices | Phone + laptop; multiple astrology apps + books |
| Belief (1–5) | 4 |
| Term comfort (1–5) | 5 |

### Bio
Self-taught jyotish enthusiast who reads his own chart, cross-checks apps against
classical texts, and times business moves by dasha/transit. Distrusts anything that
hides its working or feels dumbed-down.

### Goals
- Time business decisions with dasha/transit precision.
- Deepen his own astrological skill.
- Verify the engine against sources he trusts.

### Needs
- Full technical depth: vargas, Shadbala, Ashtakavarga, dasha trees, provenance.
- Chart-style choice and calculation conventions exposed.
- Learning material with classical citations.

### Frustrations
- Generic, shallow, "you will have a great day" apps.
- Hidden calculations; no way to verify.

### Motivations
- Mastery and self-reliance.
- Better business timing and outcomes.

### Behaviours & context
- Checks several times a week; performs remedies knowledgeably.
- **Decides himself**; uses humans rarely, as peers.

### Astrology profile
- **Checks:** business/money, property, and everything (study).
- **Wants:** *full technical detail*.
- **Remedies:** regularly, deliberately.
- **Fear-handling:** **full honesty** — he can take it.
- **Human vs app:** self-directed.
- **Actions wanted:** inspect charts/overlays, verify calculations, learn, save notes.

### Attitude dials
- Belief: 4/5 · Simple↔Technical: **Technical** · Reassurance↔Honesty: **Honesty** · Casual↔Committed: **Committed** · Routine↔Decision: **Both**

### Completed survey
- **1–5:** 35–44 · Male · Metro · Business/self-employed · English
- **6–8:** Influence 4 · Vedic + numerology · via app, website, family astrologer, YouTube
- **9–11:** Checks a few times/week · triggers: habit/decisions/curiosity · feels **informed**
- **12–15:** Areas — Money, Career, Property (top: **Money**) · Muhurtham 5 · daily timings **daily**
- **16–18:** **Detailed explanation** · text · **morning**
- **19–21:** Term comfort **5** · wants **full technical** · **learn definitely**
- **22–25:** Hard period → explanation, do's/don'ts, timing, remedies · remedies **regularly** · timing value 5 · **decides self**
- **26–29:** Trusts **calculations + reasoning + specificity** · distrusts vague + failed predictions · frightened **no** · **full honesty**
- **30–32:** Pays **regularly** · would pay for depth/learning/timing/human · **₹300–1000/mo**
- **33:** *"Which dasha/transit window is my business expansion actually in?"*
- **34:** *"Give me the real calculations — let me inspect Rashi, Navamsha, dashas — and don't dumb it down."*

### What this means for AstroSpace
The app's existing 15-tab computed workbench already serves Anand well — he's the
*current* product's best-fit user. His risk isn't features, it's the golden-chart
validation still pending: a prosumer will catch and abandon over a wrong degree.
Also the highest willingness-to-pay for *depth*.

---

## P5. Suresh — "The Matchmaking Parent"

> "Give me a clear match verdict and the remedy if there's a dosha — not vague fear. And a good muhurtham."

**Experience mode:** Balanced · **Segment:** Event-driven, high-stakes decision

### Snapshot
| | |
|---|---|
| Age | 52 |
| Location | Rajahmundry (Tier-2 city) |
| Occupation | Government/salaried employee |
| Family | Married; arranging his daughter's marriage |
| Languages | Telugu, English |
| Tech comfort | Moderate |
| Devices | Android phone |
| Belief (1–5) | 4 |
| Term comfort (1–5) | 3 (knows matching terms: nakshatra, gana, nadi, manglik) |

### Bio
Currently deep in his daughter's matchmaking. Astrology is central to vetting
alliances — kundli matching (gun milan), doshas (manglik, nadi), and fixing the
muhurtham. Anxious to get it right; will consult a trusted astrologer but wants to
pre-screen matches himself.

### Goals
- Find a compatible, dosha-clear match for his daughter.
- Understand and, if needed, remedy any dosha.
- Fix an auspicious wedding muhurtham.

### Needs
- A clear compatibility verdict, not a jargon dump.
- Honest dosha assessment **with the remedy/cancellation**, not just fear.
- Muhurtham options.

### Frustrations
- Dosha panic with no path forward.
- Astrologers who disagree; no way to sanity-check.

### Motivations
- His daughter's happy, secure marriage.
- Family reputation and doing right by tradition.

### Behaviours & context
- Currently checks **a few times a week** (active matching); normally event-only.
- Trusts a **human astrologer** for the final call; pays per-event.

### Astrology profile
- **Checks:** marriage compatibility, doshas, muhurtham; children/family.
- **Wants:** *what + brief why* — enough to trust the verdict.
- **Remedies:** sometimes; wants them when a dosha appears.
- **Fear-handling:** honest but **not blunt about divorce/failure** for his daughter.
- **Human vs app:** app to pre-screen, human to confirm.
- **Actions wanted:** run a match, read dosha + remedy, compare matches, muhurtham, consult a human.

### Attitude dials
- Belief: 4/5 · Simple↔Technical: **Middle** · Reassurance↔Honesty: **Honesty-with-care** · Casual↔Committed: **Committed** · Routine↔Decision: **Decision/event**

### Completed survey
- **1–5:** 45–54 · Male · Tier-2 city · Salaried professional · Telugu
- **6–8:** Influence 4 · Vedic jyotish · via family astrologer, panchang, temple, app (for matching)
- **9–11:** Checks a few times/week (matching) · triggers: decision/event/worry · feels **it depends**
- **12–15:** Areas — Marriage, Children, Family (top: **Marriage**) · Muhurtham 5 · daily timings only for important tasks
- **16–18:** Short paragraph / report · text · **only when I ask**
- **19–21:** Term comfort 3 · wants **"what + why"** · learn a little
- **22–25:** Hard period → explanation, remedies, consult astrologer, timing · remedies sometimes · timing value 5 · prefers **human**
- **26–29:** Trusts **calculations + specificity + reputation + referral** · distrusts vague + money-to-remove · frightened once/twice (manglik) · don't tell bluntly: divorce/marriage-failure, health
- **30–32:** Pays for **big events** (matchmaking) · would pay for match reports/human/remedies/muhurtham · **<₹100/mo** (but pays more per-event)
- **33:** *"Is this match right for my daughter, and are there doshas I should worry about?"*
- **34:** *"A clear match verdict and the remedy if there's a dosha — not vague fear. And a good muhurtham."*

### What this means for AstroSpace
The compatibility engine (gun milan, manglik, gandanta) already exists — but Suresh
needs it wrapped as a **verdict + dosha + remedy + muhurtham** flow, not raw koota
scores. This is a discrete, high-willingness-to-pay *event* (matchmaking is where
Indian families spend on astrology), and it exposes the remedy gap sharply: a dosha
with no cancellation/remedy is just anxiety.

---

## P6. Ananya — "The Gen-Z Social Follower"

> "Make it fun and shareable — tell me about ME, my vibe, my love life. Not scary temple stuff."

**Experience mode:** Guided (light/entertainment) · **Segment:** Casual, identity/social

### Snapshot
| | |
|---|---|
| Age | 23 |
| Location | Bengaluru (metro) |
| Occupation | Junior graphic designer |
| Family | Single, lives with friends |
| Languages | English |
| Tech comfort | Very high (Instagram-native) |
| Devices | Phone-only, stories/reels |
| Belief (1–5) | 2 |
| Term comfort (1–5) | 2 (knows pop-astro: rising sign, mercury retrograde) |

### Bio
Consumes astrology as identity, aesthetic and social currency — daily horoscope
scrolls, memes, "big three," compatibility with crushes. Leans Western pop-astrology
more than classical Vedic. Low belief, high engagement; it's entertainment and
self-reflection, not decision-making.

### Goals
- Understand herself and her relationships in a fun way.
- Shareable, aesthetic content for social.

### Needs
- Short, visual, story-card format.
- Personality + love/compatibility focus, about *her*.
- Playful, never doom-y.

### Frustrations
- Heavy, ritualistic, fear-based "temple" tone.
- Long text, dense jargon, ugly UI.

### Motivations
- Self-expression and belonging.
- Curiosity and fun.

### Behaviours & context
- Scrolls **daily** casually; feels it's **entertainment**.
- **Decides herself**; won't pay (freemium expectation).

### Astrology profile
- **Checks:** love/compatibility, personality, general luck, career (lightly).
- **Wants:** *just tell me, lightly*.
- **Remedies:** once or twice (crystals, aesthetic).
- **Fear-handling:** doesn't take it seriously; wants it light.
- **Human vs app:** self; app/social.
- **Actions wanted:** daily card, share, compatibility with a crush, "my chart" personality.

### Attitude dials
- Belief: 2/5 · Simple↔Technical: **Simple** · Reassurance↔Honesty: **Light/honest** · Casual↔Committed: **Casual** · Routine↔Decision: **Routine (casual)**

### Completed survey
- **1–5:** 18–24 · Female · Metro · Salaried professional · English
- **6–8:** Influence 2 · sun-sign + tarot + numerology (dabbles) · via app, social, WhatsApp
- **9–11:** Checks **daily** (casual) · triggers: habit/curiosity/relationship worry · feels **it depends**
- **12–15:** Areas — Relationships (love), Career, Daily luck (top: **Relationships**) · Muhurtham 2 · daily timings **never**
- **16–18:** **One line** · story cards + infographics · **morning**
- **19–21:** Term comfort 2 · wants **"just tell me" (light)** · learn a little (about her chart)
- **22–25:** Hard period → reassurance, explanation · remedies once/twice · timing value 2 · **decides self**
- **26–29:** Trusts specificity + accuracy + friend-referral · distrusts vague/fear/pushy · frightened **no** · **full honesty (playful)**
- **30–32:** Pays **never** · would maybe pay for compatibility/"my chart" · **nothing–under ₹100/mo**
- **33:** *"Are we actually compatible, or should I move on?"*
- **34:** *"Make it fun and shareable, not scary. Tell me about my personality and my love life."*

### What this means for AstroSpace
The acquisition/virality segment — but a **partial fit**: she wants Western pop-astro
identity content (big-three, personality, shareable cards), and AstroSpace is Vedic
and serious. Serving her means a *different content surface* (visual, share-first,
personality/compatibility) that may or may not be worth building. Decision: is she a
target, or an acquisition funnel we deliberately don't chase yet? Low monetization,
high potential reach.

---

## P7. Meera — "The Diaspora Anchor"

> "Give me correct timings for MY timezone, US festival dates, remedies I can do here, and a real astrologer when I need one."

**Experience mode:** Balanced · **Segment:** NRI, tradition-across-distance

### Snapshot
| | |
|---|---|
| Age | 38 |
| Location | New Jersey, USA (metro) |
| Occupation | Pharma/IT professional |
| Family | Married, two young children; aging parents in Hyderabad |
| Languages | English (primary), Telugu (heritage) |
| Tech comfort | High |
| Devices | Phone + laptop |
| Belief (1–5) | 4 |
| Term comfort (1–5) | 3 |

### Bio
Moved from Hyderabad; wants to keep her family connected to tradition despite
distance and timezone. Juggles US life with Indian observances — festivals on the
right (US) date, muhurtham across timezones, kids' name selection, and worry about
parents' health back home. Time-poor, higher disposable income.

### Goals
- Keep her kids and household connected to tradition abroad.
- Correct festival dates and muhurtham for her timezone.
- Peace of mind about parents back home.

### Needs
- Timezone-correct panchang, muhurtham, and festival dates (US).
- Remedies feasible abroad (no specific temple/materials).
- A bridge to a trusted astrologer back home when needed.

### Frustrations
- Panchang/timings computed for India, wrong for her timezone.
- Festival dates that don't match her local observance.
- Being far from the family astrologer.

### Motivations
- Cultural continuity for her children.
- Duty to and worry about aging parents.

### Behaviours & context
- Checks a few times a week + festivals; **mix** of app (daily) + human (big).
- Higher willingness to pay (USD); time-poor, wants efficiency.

### Astrology profile
- **Checks:** children, parents' health, festivals/muhurtham, career.
- **Wants:** *what + why*.
- **Remedies:** sometimes; needs abroad-feasible ones.
- **Fear-handling:** careful on parents' health/death, children.
- **Human vs app:** app for daily, human (back home) for serious.
- **Actions wanted:** timezone panchang/muhurtham, festival reminders, remedies, connect to astrologer, kids' charts.

### Attitude dials
- Belief: 4/5 · Simple↔Technical: **Middle** · Reassurance↔Honesty: **Balanced** · Casual↔Committed: **Committed** · Routine↔Decision: **Both**

### Completed survey
- **1–5:** 35–44 · Female · Metro (US) · Salaried professional · English
- **6–8:** Influence 4 · Vedic jyotish · via app, website, family astrologer (remote), panchang
- **9–11:** Checks a few times/week + festivals · triggers: habit/decision/event/worry · feels **informed**
- **12–15:** Areas — Children, Family (parents), Career (top: **Children**) · Muhurtham 5 · daily timings sometimes
- **16–18:** Short paragraph · text + audio · **morning (local TZ)**
- **19–21:** Term comfort 3 · wants **"what + why"** · learn a little
- **22–25:** Hard period → do's/don'ts, remedies (abroad-feasible), timing, consult astrologer · remedies sometimes · timing value 5 · prefers **mix**
- **26–29:** Trusts **calculations + specificity + reputation + referral** · distrusts vague + money-to-remove · frightened once/twice · don't tell bluntly: parents' health/death, children
- **30–32:** Pays **occasionally / for events** · would pay for timing/human/reading/daily · **₹300–1000/mo equivalent**
- **33:** *"Are my parents back home okay, and will my kids settle well here?"*
- **34:** *"Correct timings for my timezone, US festival dates, remedies I can do here, and a real astrologer when I need one."*

### What this means for AstroSpace
Exposes a **technical gap: timezone/geo correctness** for panchang, muhurtham and
festivals — the engine defaults to birth/India place. Diaspora is a high-value,
higher-paying segment underserved by India-centric apps. Also reinforces the
festival-calendar and remedy features, plus a future "connect to an astrologer"
marketplace.

---

## Cross-persona synthesis → product decisions

**1. Experience mode keys off complexity-appetite, not belief.** Lakshmi (belief 5)
and Anand (belief 4) are opposite users; Padma (devout) and Ravi (skeptic) both want
it simple. Drive `experienceMode` off **term-comfort (Q19) + "want the why" (Q20)**.
Default **Guided/Balanced**; Practitioner is opt-in (only Anand).

**2. The "what to do" layer is the biggest shared gap.** Every persona's hard-period
answer wants **remedies and/or timing**; five of seven perform remedies. Remedies +
goal-based muhurta aren't nice-to-haves — they're table stakes for six of seven.
The app is descriptive; the users want prescriptive.

**3. Fear-handling must be a per-mode setting, not a global tone.** Lakshmi, Padma,
Suresh, Meera → protect me (no blunt health/death/kids/marriage). Ravi, Anand →
full honesty. The *same* dosha needs two deliveries. This is safety + product.

**4. Language + audio are functional requirements for the core.** The Guided core
(Lakshmi, Padma) needs **Telugu + audio**; the app is English-text-only. This is a
reach blocker for the exact audience Guided targets.

**5. Distinct high-value *event/segment* surfaces the engine already half-supports:**
- **Matchmaking (Suresh):** verdict + dosha + remedy + muhurtham flow over the
  existing compatibility engine. Highest per-event spend.
- **Festival/observance calendar (Padma, Lakshmi, Meera):** retention + daily habit.
- **Timezone/geo correctness (Meera):** unlocks the higher-paying diaspora segment.

**6. Monetization maps cleanly to modes:** Practitioner pays for *depth* (Anand,
₹300–1000); believers pay for *remedies, timing, human connection, events* (Suresh,
Meera); skeptics pay only *after trust* (Ravi); casual/social barely pays (Ananya) —
her value is reach, not revenue.

**7. One deliberate scoping call:** Ananya (Gen-Z, Western pop-astro, share-first) is
a different content product. Decide explicitly whether she's a target or a
funnel-we-don't-chase-yet — don't let her requirements distort the Vedic core.

**Validate first with real users:** the honesty-vs-gentleness split (Ravi/Anand vs
the rest), the Telugu/audio demand, and the willingness-to-pay bands — these drive
big build decisions and are exactly where synthetic personas are least reliable.
