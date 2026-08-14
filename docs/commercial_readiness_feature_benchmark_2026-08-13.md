# Siddha Commercial Readiness Benchmark and Feature Inventory

**Date:** 2026-08-13  
**Status:** product discovery and evidence-based planning; not an implementation claim  
**Scope:** Siddha mobile app, supporting backend, Context Engine, administration,
commercial model, and operational readiness

## Executive position

Siddha should not try to win by becoming the largest menu of astrology
calculators. AstroSage and Cosmic Insights already compete strongly on breadth;
AstroTalk competes on access to human astrologers; CHANI and The Pattern compete
on editorial voice, ritual, reflection, and retention; TimePassages competes on
clear professional-grade chart exploration.

Siddha's credible differentiation is the combination of:

1. deterministic and source-aware Vedic calculation;
2. one product that changes depth for Guided, Balanced, and Practitioner users;
3. daily, calendar, remedy, muhurta, and Ask guidance connected to the same
   profile and conventions;
4. an honest Context Engine that remembers user-confirmed life context without
   treating disclosure as proof of astrology; and
5. a calm native experience that remains useful when the network or model is
   slow.

The codebase already contains unusually broad computation and many screens, but
it is **not commercially ready**. The launch blockers are not another 20 chart
techniques. They are durable local data, lifecycle/session reliability,
location-correct calendar behavior, entitlement enforcement, profile-memory
governance, runtime observability, accessibility, privacy controls, and a
release-grade regression program.

## Since this audit

This document is a point-in-time benchmark against commit `c7b6095`. The
following work landed after the audit and supersedes the corresponding status
cells below without changing the original research record:

- **Reliable Native Core:** encrypted, identity-scoped native resource caching
  now exists with schema/version metadata, stale-while-revalidate behavior,
  logout/profile invalidation, race protection, and sunrise-aware Today
  validity. It has Android device evidence; physical iOS validation and wider
  endpoint adoption remain open.
- **Profile Context Ledger:** the architecture, privacy contract, frozen-request
  evidence model, and rollout gates are documented and merged. The database,
  APIs, preflight integration, user controls, and encrypted sync are **not yet
  implemented**.
- **Ask safety parity:** the non-streaming web Ask route now uses the same
  orchestrator and safety boundary as native streaming Ask; boundary states are
  preserved and rendered distinctly.
- **Commercial entitlements:** a server-authoritative entitlement and plan
  architecture has been specified. Store integration, billing webhooks,
  enforcement, quota accounting, restore/grace behavior, and approved product
  pricing remain implementation work.

Where a table below says **Missing** or **Partial** for one of these areas, use
this addendum as the current status and treat the table as the original audit
snapshot.

## Research method and limits

- Competitor capabilities were checked against official product sites, official
  help centers, and current App Store/Google Play descriptions on 2026-08-13.
- Architecture recommendations use official Android, Apple, Google Play,
  StoreKit, Capacitor-adjacent, RevenueCat, and OWASP guidance.
- Siddha status is based on repository inspection of `ui/src/app/features/mobile`,
  `ui/src/app/core`, `astrospace`, migrations, routes, tests, and existing audit
  documents at commit `c7b6095`.
- **Implemented** means a real code path exists. It does not automatically mean
  production data, native permissions, store configuration, or device behavior
  has been re-verified for this report.
- Market pricing and store offerings change. This document treats them as
  directional benchmark signals, not pricing instructions.

## Status legend

| Status | Meaning |
|---|---|
| **Verified** | Code plus focused test/device/audit evidence exists in this repository. |
| **Implemented** | A substantive code path exists; this research did not re-run it end to end. |
| **Partial** | Some UI/schema/service exists, but the capability is incomplete or not operational. |
| **Planned** | Documented/design/schema intent exists without a complete user-facing capability. |
| **Missing** | No meaningful implementation found. |
| **Defect** | Existing behavior has a documented or structurally evident release-blocking gap. |
| **Risk-gated** | Valuable, but must not ship before accuracy, safety, privacy, legal, or commercial controls. |
| **Defer** | Deliberately not recommended for the near-term roadmap. |

Priority uses `P0` launch blocker, `P1` core commercial capability, `P2`
important differentiation/retention, and `P3` later optimization.

## Market benchmark

| Product/archetype | Current product signal | What Siddha should learn | What Siddha should not copy |
|---|---|---|---|
| [Cosmic Insights](https://cosmicinsights.app/) | Deep Vedic charts, 16+ vargas, advanced strengths, many dashas, panchanga, muhurta, remedies, offline charts, reminders, exports, profile scale, and tiered add-ons | Practitioner depth, offline chart access, calculation controls, precise alerts, profile organization | A catalogue so dense that a Guided user cannot form a clear next action |
| [AstroSage Kundli](https://www.astrosage.com/mobileapps/astrosage-kundli-best-astrology-app-by-astrosage.asp) | Very broad Vedic feature set, PDF Kundli, matching, panchang, consultation, nine languages, large distribution | Regional language ambition, printable reports, broad India-market expectations | Advertising/shop clutter, fear-based upsell, and uncurated technique sprawl |
| [Drik Panchang](https://www.drikpanchang.com/settings/drikpanchang-settings.html?lang=en) | Location-sensitive panchanga, user-selectable festival/fast/event categories, custom locations, detailed daily timings | Calendar correctness, observance preference depth, global location handling, transparent timing settings | Turning Siddha's primary experience into a technical almanac |
| [TimePassages](https://timepassages.astrograph.com/astrology-software) | Beginner-to-professional chart reading, point-and-click interpretations, transits/progressions, compatibility, search/recents, cloud sync | Every technical object should be tappable and explainable; search and recents matter for many profiles | Western techniques that dilute Siddha's Vedic convention contract |
| [CHANI](https://www.chani.com/app?view=home) | Daily and weekly guidance, chart readings, transit timing, meditations, affirmations, journal prompts, audio, clear free/premium split | Ritual, editorial quality, listening, reflection, and a coherent recurring-use loop | Generic wellness content disconnected from computed profile context |
| [The Pattern](https://www.thepattern.com/) | Personal patterns, relationship Bonds, past/future Time Travel, community, audio, AI conversation | Life-stage storytelling, retrospective timelines, relationship exploration, understandable language | Social/dating expansion before privacy and core prediction trust are mature |
| [AstroTalk](https://apps.apple.com/in/app/astrotalk-talk-to-astrologer/id1208433822) | Chat/call/live marketplace, matching, free Kundli/horoscopes, per-minute monetization | Human escalation can be a future trust and revenue path | Marketplace incentives, unverified quality, product sales, or urgency-based monetization now |
| [Headspace](https://help.headspace.com/hc/en-us/articles/115008361288-How-do-I-download-sessions-in-advance-for-offline-use) | Downloaded offline sessions, structured content library, family plan | Explicit offline library and family-account mechanics | Treating astrology guidance as interchangeable meditation content |
| [Day One](https://dayoneapp.com/features/end-to-end-encryption/) | Encrypted personal memory, multi-device sync, export, user ownership | Sensitive profile memory needs encryption, export, deletion, and user control | Storing inferred life facts invisibly because personalization is useful |
| [Clue](https://support.helloclue.com/hc/en-us/articles/29216023055645-What-is-Clue-s-stance-on-data-privacy) | Granular privacy controls and explicit treatment of sensitive user-entered data | Consent-by-purpose, transparency, data minimization, revocable memory | Ambiguous consent bundled into general terms |

## Product principles derived from the benchmark

1. **Trust before breadth.** Calculation provenance, known limits, stale-data
   labels, and honest agent boundaries are never premium-only.
2. **Local-first reading.** Android recommends a persisted local source as the
   read source of truth for offline-first apps, with network synchronization
   updating it. Siddha's current `localStorage` caches are a useful bridge, not
   that architecture ([Android offline-first guidance](https://developer.android.com/topic/architecture/data-layer/offline-first)).
3. **Profile facts before astrology.** Age, life stage, relationship state,
   dependants, location, occupation, and user-confirmed events constrain the
   interpretation before chart synthesis. The system must never predict a
   future career start for a retired person because it ignored ordinary logic.
4. **Memory is user-owned.** Every durable memory needs source, confidence,
   scope, sensitivity, confirmation state, edit/delete controls, retention,
   and a visible explanation of where it was used.
5. **Native means lifecycle-correct.** Safe areas, keyboard, back gestures,
   background/resume, secure storage, notifications, offline reads, sharing,
   and accessibility are product behavior, not packaging details. Apple calls
   out safe areas as essential to avoiding system UI and interactive bars
   ([Apple layout guidance](https://developer.apple.com/design/human-interface-guidelines/layout)).
6. **Entitlements are server-authoritative.** The client may optimize display,
   but purchased access must be validated and mapped to stable capabilities,
   not scattered `if plan == ...` checks.
7. **No paid certainty.** Higher plans may unlock depth, convenience, history,
   and scale; never stronger claims, fear removal, safety guidance, or hidden
   calculation truth.

## Master feature checklist

### A. Positioning, trust, and product comprehension

| Capability | Siddha status/evidence | Benchmark signal | Next acceptance gate | Pri. / risk |
|---|---|---|---|---|
| One-sentence product promise: “a Vedic way-of-life guide” | **Partial** — renamed and revised onboarding exists, but product surfaces still mix astrology workbench and life-guide language | CHANI owns a coherent wellbeing story; TimePassages owns chart expertise | Every store, onboarding, paywall, and empty state states the same job-to-be-done | P0 |
| Explicit “what Siddha can/cannot do” | **Partial** — disclaimers and Ask refer-outs exist | Trust-oriented apps explain limitations before sensitive use | Plain-language capabilities, prohibited outcomes, data use, and human-help boundary | P0 / safety |
| Calculation provenance per result | **Implemented** — source/provenance sheets and CE references exist | TimePassages emphasizes human interpretation; practitioners expect traceability | Every technical/predictive card exposes calculation inputs and sources consistently | P1 |
| Convention transparency | **Implemented, unverified end to end** — settings and ayanamsha/node inputs exist | Practitioner tools expose calculation settings | Show effective convention on every export/Ask context and test persistence across devices | P0 / wrong-results |
| Confidence and evidence disclosure | **Partial** — structured Ask reading has confidence/evidence; other modules vary | Trust requires distinguishing computed fact, tradition, and inference | Shared confidence/provenance vocabulary across Today, Ask, remedies, muhurta, compatibility | P1 |
| Correction/feedback loop | **Planned/partial** — validation probe architecture exists behind a flag | The Pattern uses reflection; predictive products need outcome learning | User can mark helpful/wrong/outdated with reason; feedback never silently rewrites truth | P1 / bias |
| Accuracy methodology page | **Missing** | Professional products communicate authorship and calculation approach | Public methodology, conventions, test chart set, source policy, correction log | P1 |
| Public incident/status communication | **Missing** | Commercial services need visible reliability posture | Status page, incident templates, in-app service degradation banner | P1 |

### B. Account, onboarding, identity, and profiles

| Capability | Siddha status/evidence | Benchmark signal | Next acceptance gate | Pri. / risk |
|---|---|---|---|---|
| Email/password registration and sign-in | **Implemented** — mobile auth and Supabase service | Table stakes | Device test: cold boot, expiry, offline resume, password reset, account switching | P0 |
| Google sign-in with native callback | **Implemented** — Capacitor Browser/deep-link flow and nonce handling | Table stakes | Verify iOS/Android release schemes, cancellation, replay, browser return, multiple accounts | P0 / security |
| Durable native session | **Partial** — foreground refresh fix exists; recent user reports showed repeated sign-out | Native apps must survive suspension and network handoff | Seven-day soak, token-expiry, process death, reboot, offline/online matrix | P0 |
| Welcome/language/persona/customize/birth-details/Aha flow | **Implemented/partial** — routes exist; screen tracker still records persona and state gaps | Strong products prove value during onboarding | Persona-specific Aha with real calculation, resumable onboarding, no dead carousel controls | P0 |
| Native DOB/TOB and real place selection | **Implemented, needs global validation** | Vedic accuracy depends on exact inputs | Native controls, timezone/DST ambiguity, historical place/timezone validation, manual fallback | P0 / wrong-results |
| Unknown/approximate birth time | **Missing** — existing build plan marks absent | Serious astrology apps distinguish uncertainty | Explicit unknown/approximate state; disable or qualify time-sensitive outputs; rectification path | P0 / wrong-results |
| Multiple profiles | **Implemented** — Kundli store and management routes | TimePassages/Cosmic Insights support stored charts | Define plan quotas; fast switching; no cross-profile cache/thread/memory leakage | P0 / privacy |
| Relationship to account owner | **Partial** — `relation` appears in Kundli UI/store; governance unclear | Family and compatibility products need explicit relation | Structured self/partner/child/parent/client relation, consent and minor handling | P1 / privacy |
| Profile archive vs delete | **Partial** — deletion flow exists; archive noted missing | User-controlled lifecycle | Archive, restore, hard-delete, retention preview, dependent Ask/report handling | P1 |
| “Today across profiles” dashboard | **Missing** — tracker records absent | Family products make profile scale useful | Consent-aware summary with alert severity limits and no sensitive detail leakage | P2 |
| Cross-device profile sync | **Implemented at server, partial UX** | TimePassages advertises one-login chart sync | Conflict handling, loading strategy, offline create/edit queue, deterministic cache invalidation | P1 |
| Profile import | **Missing** | Practitioner users have many existing charts | CSV/JSON import first; validation report; AstroSage/Cosmic formats only if legally/technically feasible | P2 |
| Profile export/portability | **Missing/partial schema** — share assets exist, no complete user export | Day One makes export a trust feature | Export profile, conventions, charts, Ask, memories, notes as JSON/PDF with redaction choices | P0 / privacy |
| Age/minor consent policy | **Missing** | Sensitive-data apps define minimum age and guardian rules | Age gate, minor profile ownership rules, Ask restrictions, deletion/consent workflow | P0 / legal |

### C. Native application foundation

| Capability | Siddha status/evidence | Benchmark signal | Next acceptance gate | Pri. / risk |
|---|---|---|---|---|
| Capacitor Android/iOS packaging | **Implemented** | Baseline only | Reproducible signed builds from clean checkout, version provenance, store tracks | P0 |
| Safe-area contract across all routes/overlays | **Partial/defect history** — multiple prior bottom-nav/overlay reports; CSS/native work exists | Apple requires layouts to respect system safe areas | Automated device matrix: gesture/3-button nav, cutouts, keyboards, sheets, auth, landscape policy | P0 |
| Android system back | **Partial** | Native expectation | Route-aware back, close sheet first, chat-to-gateway behavior, no accidental app exit | P0 |
| iOS swipe-back and interactive dismissal | **Unverified** | Native expectation | Gesture QA with unsaved forms, streams, sheets, and nested chart pages | P1 |
| Keyboard/inset handling | **Partial/defect history** — Ask composer positioning repeatedly failed | Chat experience benchmark | Composer anchored above IME on Android/iOS, no jump, resize, or hidden send control | P0 |
| Disable WebView text/link drag leakage | **Implemented in recent native work, not re-verified here** | Native apps should not expose browser affordances | Long-press matrix on cards, links, charts, selectable/copyable answer text | P1 |
| Secure device storage | **Missing** — Preferences plugin exists, but substantial data uses WebView `localStorage`; no encrypted DB found | OWASP MASVS requires secure sensitive storage | Keychain/Keystore for secrets; encrypted native database for sensitive profile/Ask cache | P0 / security |
| Local structured database | **Missing** | Android offline-first guidance recommends a persisted local source of truth | SQLite/Capacitor DB schema, migrations, repositories, eviction, per-user encryption boundary | P0 |
| Network state awareness | **Missing** — no Capacitor Network dependency found | Offline-first apps distinguish unavailable/stale/refreshing | Connectivity observer, offline banner, retry/backoff, queued writes | P0 |
| Background synchronization | **Missing** | Android recommends persistent work for queued sync | WorkManager/BGTask design with battery/data constraints and idempotency | P1 |
| Native share sheet | **Partial** — copy/share UI and share schema; no Capacitor Share dependency found | Charts/reports are naturally shareable | Native share image/PDF/link, redaction preview, expiring token, revoke share | P1 / privacy |
| Biometric app lock | **Missing** | Day One protects highly personal content | Optional Face ID/Touch ID/biometric lock with secure fallback | P1 / privacy |
| Push notifications | **Partial** — preferences/jobs/schema/UI exist; UI says native delivery is not connected | Daily/calendar apps depend on timely alerts | APNs/FCM registration, permission education, delivery receipts, quiet hours, deep links | P0 |
| Local notifications | **Missing** | Mantra/remedy/calendar reminders should work without server round-trip | Device scheduler, timezone changes, missed notification reconciliation | P1 |
| Haptics toggle | **Implemented** | Native polish | Ensure all haptics route through service and respect system/reduced feedback | P2 |
| App shortcuts/deep links | **Partial** — auth deep link exists; feature deep-link matrix absent | Faster recurring use | Today, Ask, Calendar Day, remedy practice; auth and entitlement gates | P2 |
| Home/lock widgets, live activity, watch | **Planned/schema only** — widget/live activity tables; build plan says not built | Cosmic Insights has watch alerts; daily apps benefit from glanceability | Ship only after core cache, location correctness, push, and privacy redaction are proven | P3 / privacy |
| Native accessibility semantics | **Partial/unverified** | Apple/Android commercial baseline | TalkBack/VoiceOver route sweep, focus order, dynamic text, chart alternatives | P0 |

### D. Performance, caching, offline, and data freshness

| Capability | Siddha status/evidence | Benchmark signal | Next acceptance gate | Pri. / risk |
|---|---|---|---|---|
| In-memory request de-duplication | **Implemented** — `VedicService` Promise maps | Baseline performance | Cancellation, bounded memory, profile/session invalidation tests | P1 |
| Persisted chart cache | **Partial** — versioned `localStorage` for `/all`; detail caches mainly memory-only | Cosmic Insights advertises offline charts | Native DB, metadata/TTL/schema version, stale-while-revalidate, encryption | P0 |
| Persisted Today cache | **Implemented/partial** — location/date keyed localStorage plus server cache model | Offline-first should render local immediately | Show cache age/source, background refresh, expiry, profile/account scoping | P0 |
| Persisted calendar cache | **Implemented/partial** — date/location/options key in localStorage | Drik Panchang can work offline | Month-partitioned DB cache, instant selected month, prefetch adjacent months, stale labels | P0 |
| Festival cache | **Implemented/partial** — localStorage by city/date/days; region filtered client-side | Calendar must feel instant | Version/freshness metadata, region taxonomy, server invalidation, observance calendar version | P1 |
| Ask history local cache | **Partial** — session maps/thread service; durable offline conversation store not found | Chat users expect immediate history | Encrypted local thread/message DB, sync cursor, tombstones, profile isolation | P0 / privacy |
| Stale-while-revalidate UI | **Partial** — some screens apply cache first; generic stale state tracker remains open | Android recommends local reads followed by sync | One shared resource model: loading/content/stale/error/refreshing/offline | P0 |
| Cache invalidation on birth edits | **Implemented** — KundliStore calls Vedic invalidation | Correctness requirement | Server cache invalidation and multi-device version token tested | P0 / wrong-results |
| Cache invalidation on convention edits | **Partial** — keys include ayanamsha/node; location keys included for daily/calendar | Correctness requirement | Matrix for chart style vs calculation conventions vs location vs language | P0 |
| Cache invalidation on current-location change | **Implemented/partial** — `panchangaContextKey`, query keys; no GPS observer | Location-sensitive calendar benchmark | Automatic location opt-in, manual pin, timezone move, DST and day-boundary tests | P0 / wrong-results |
| Cache quota/eviction | **Missing** — localStorage failures are swallowed | Commercial app cannot grow unbounded or fail silently | LRU/size budgets, per-resource retention, user-visible download/storage controls | P1 |
| Cache encryption and account isolation | **Missing/risky** | Sensitive guidance must not survive account switch in readable WebView storage | Per-user encrypted namespace, wipe on logout/account delete, adversarial tests | P0 / privacy |
| Precompute after profile creation/edit | **Partial** — `/vedic/{id}/all` and caches exist; no durable job/readiness manifest found | User asked to avoid recomputation per tab | Calculation manifest, background job, progress screen, partial availability, retry | P1 |
| Server cache strategy | **Partial** — DailyGuidanceCache model; no general result cache contract | Expensive deterministic computations should be reusable | Content-addressed calculation hash, Redis/DB policy, TTL/invalidation, hit-rate metrics | P1 |
| Latency budgets | **Missing** | Commercial products manage p50/p95, not impressions | Budget: shell <1s cached, tabs <300ms cached, network content p95 targets, Ask first-event target | P0 |
| Request tracing/performance telemetry | **Missing** — no mobile analytics/APM integration found | Required to diagnose 5–10s screens | Correlation IDs, screen/API spans, cache hit/miss, provider latency, anonymized dashboards | P0 |

### E. Today and recurring guidance

| Capability | Siddha status/evidence | Benchmark signal | Next acceptance gate | Pri. / risk |
|---|---|---|---|---|
| Personalized daily guidance | **Verified/implemented** — deterministic daily payload, persona UI, caching | CHANI/TimePassages make daily personalization a free habit loop | Location and date-boundary golden tests; explain score and strongest factor | P0 |
| Current location for Today; birth location for natal chart | **Implemented in client parameters, needs end-to-end proof** | Location-correct panchanga is mandatory | Visible “calculated for” place, change action, location timestamp, no silent fallback | P0 / wrong-results |
| What Matters Today summary | **Implemented** | Editorial clarity benchmark | Eliminate repetition, cap density by persona, stale/offline badge | P0 |
| Weighted day score with plain-language reason | **Partial** — user reported equal weighting/poor explanation; later work exists | Scores need causal explanation | Document deterministic weighting, dominant bala/factor, no false precision, tests | P1 / trust |
| Do/Avoid guidance | **Implemented** | Actionability is differentiator | Deduplicate, tie each item to source/context, avoid high-stakes imperatives | P1 |
| Listen to your day | **Implemented** — device TTS service and voice settings | CHANI/Headspace normalize audio | Lock-screen controls, pause/resume, offline TTS behavior, accessibility transcript | P1 |
| Reflection prompts | **Implemented/partial** — Reflect with Siddha links to Ask | CHANI journal prompts drive retention | Save reflection as profile-private journal entry; do not automatically treat as durable fact | P2 / privacy |
| Birth signature/constants | **Verified recent UI work** | Persistent self-understanding | Clarify constants vs daily signals; accessible grid and export | P1 |
| Week-ahead guidance | **Missing** | CHANI and horoscope products use weekly cadence | Deterministic 7-day view from cached calendar/transits; no new LLM dependency | P2 |
| Monthly/yearly outlook | **Partial across calendar/transits/readings** | Market expectation | One coherent timeline with evidence, uncertainty, and past/future navigation | P2 / prediction risk |
| Journal/check-in | **Missing** | CHANI, The Pattern, Day One | Private entries, optional tags, memory promotion workflow, encrypted/exportable | P2 / privacy |

### F. Calendar, panchanga, festivals, and muhurta

| Capability | Siddha status/evidence | Benchmark signal | Next acceptance gate | Pri. / risk |
|---|---|---|---|---|
| Month calendar | **Implemented/defect history** — cache exists, repeated load/date-routing bugs reported | Google Calendar and Drik Panchang set interaction baseline | Instant cached month, correct selected date, swipe navigation, timezone tests | P0 |
| Day/week/month modes | **Missing** | Google Calendar supports day/week/month offline | Day agenda, 7-day signal strip, month grid sharing one selected-date state | P1 |
| Swipe month navigation | **Missing/planned by user** | Native calendar expectation | Gesture thresholds, animation, prefetch, accessibility alternative | P1 |
| Panchanga five limbs and timings | **Implemented** | Drik Panchang depth | Golden validation by location/date; visible timezone, sunrise convention, source/version | P0 / wrong-results |
| Global city/place search | **Partial** — city API, 160 result cap, state-place tests | Drik supports add-new-location with coordinates | Global geocoder, diacritics, duplicate city disambiguation, manual lat/lon/timezone fallback | P0 |
| Automatic current location | **Missing/partial** — manual preference exists; geolocation plugin not found | Local panchanga should follow actual place with consent | Approximate vs precise choice, permission states, travel detection, manual lock | P1 / privacy |
| Festival catalogue | **Implemented/partial** — models, endpoints, settings, regional filters | Drik offers granular festival/fast/event categories | Audited taxonomy by region/tradition, versioned source, fixture coverage for representative states | P0 / cultural accuracy |
| Multi-ethnic/multi-tradition selection | **Partial** — regions limited to pan-India/north/south | Drik exposes individual observances | State + sampradaya + individual observance selection, additive not mutually exclusive | P1 |
| Festival detail: meaning, what/how/mantra | **Implemented/partial** — sheet exists; prior audit found missing depth | Ritual guidance must be useful and safe | Complete content contract, regional variants, source, preparation, accessibility/audio | P1 |
| Festival reminders/observance tracking | **Partial schema/API** — user observances and notification jobs | Retention opportunity | Add to device calendar, reminder time, observed/skipped, next recurrence | P1 |
| Red-dot/calendar signal semantics | **Defect history** — user could not understand dots | Calendar markers must be legible | Legend, layered marker system, filter controls, no unexplained decoration | P1 |
| Muhurta goal catalogue | **Implemented/partial** — several goals and custom intent | Vedic apps include auspicious date finder | Expand with sourced samskara/event rules: griha pravesha, upanayana, vivaha, namakarana, etc. | P1 / cultural accuracy |
| Custom “something else” intent | **Partial** — free text falls back to general panchanga | Users need context without false specificity | Classify to supported rule set or clearly return general screening; never imply custom ceremony logic | P1 |
| Date/range picker | **Implemented/partial** | Baseline | Native date/range controls, timezone display, persisted draft, no CTA overlap | P1 |
| Muhurta saved windows | **Partial schema** | Commercial retention | Save, compare, annotate, share, reminder, recalculate on place/convention change | P2 |
| Calendar interoperability | **Missing** | Users organize life in device calendars | Export ICS/add to Apple/Google calendar with source/timezone and revocation notes | P2 |

### G. Ask, Context Engine, and profile memory

| Capability | Siddha status/evidence | Benchmark signal | Next acceptance gate | Pri. / risk |
|---|---|---|---|---|
| Structured answer contract | **Verified/implemented** — acknowledgment, basis, interpretation, summary, guidance | Better than generic chat when rendered well | Schema version compatibility, migration renderer, no markdown leakage/truncation | P0 |
| Domain routing and registry gate | **Implemented** — 7 configured of 11 taxonomy domains | Honest specialization is a differentiator | Unsupported domain state, routing eval set, no default-to-career/general answer | P0 / safety |
| Configured domains: career, marriage, wealth, children, health, foreign, personality | **Implemented** | High-demand core coverage | Golden questions, persona tests, evidence sufficiency, retrospective and life-stage tests per domain | P0/P1 |
| Unconfigured: education, family property, litigation, spirituality | **Planned taxonomy only** | Breadth can follow trust | Enable one at a time only after KB/addendum/verifier/route/device review | P2 / safety |
| Multi-turn thread continuity | **Implemented/defect history** | Chat baseline | Reopen without resend, append follow-up to same thread, full transcript, stop/retry/edit branch semantics | P0 |
| Profile/thread isolation | **Verified fixes exist** | Privacy baseline | Attacker-side races: switch mid-stream, stale fetch, account switch, offline cache | P0 / privacy |
| Archive/delete conversation | **Implemented/partial** — history swipe/archive work exists; lifecycle had gaps | Chat baseline | Active/archived tabs, undo/restore, hard delete, sync/tombstone behavior | P1 |
| Copy/share answer | **Implemented/partial** | Chat baseline | Preserve sections/citations, native share, redaction, share expiration | P1 / privacy |
| Edit question/regenerate | **Partial/unclear** | Chat baseline | Editing creates explicit branch/version; never silently mutates historical evidence | P2 |
| Stop streaming | **Implemented after prior defects, revalidation needed** | Chat baseline | Abort provider and UI consistently; partial answer labeled and not persisted as complete | P0 |
| Voice input | **Partial** — listening UI exists; actual speech recognition remained open in audit | Mobile accessibility/convenience | Native speech permission, live transcript, edit before send, language support, clear unsupported state | P1 / privacy |
| Device voice selection/TTS | **Implemented/partial** — native TTS and dedupe work | Audio is a retention feature | Stable unique voice labels, preview, locale matching, fallbacks, no server voice leakage | P1 |
| Dynamic suggested questions | **Partial** — static/persona chips found; context-derived suggestions limited | The best next question should follow current context | Generate deterministically from available domains, current period, and thread; suppress repetitive/unsafe prompts | P1 |
| Persona register and depth | **Implemented** — mode reaches backend and renderer varies basis depth | Core Siddha differentiation | Contract tests across all domains: same facts, different language/depth, no information loss | P0 |
| User tone preference | **Partial** — gentle/direct preference exists; complete request wiring needs proof | Personalization expectation | Tone must affect wording only, never factual confidence or safety | P1 |
| Life-stage/demographic reasoning | **Implemented/partial** — recent tense/profile facts work exists after retirement failure | Logical context must precede astrology | Age, retirement, occupation, relationship, dependants, residence, current date validated before model call | P0 / trust |
| Profile memory store | **Missing** — no durable governed fact/memory entity found | Clue/Day One show sensitive data needs explicit governance | Typed profile facts and episodes with source, confirmation, sensitivity, validity interval, provenance | P0 / privacy |
| Memory extraction from conversation | **Risk-gated** | Useful for continuity but high privacy/error risk | Candidate extraction only; user reviews before durable save; no inference promoted as fact | P0 / privacy |
| Memory controls | **Missing** | User ownership benchmark | “What Siddha remembers,” edit/delete, pause memory, per-thread exclusion, data export | P0 / privacy |
| Temporal facts | **Missing** | “I am unwell now” must expire or be updated | `valid_from`, `valid_to`, status, last-confirmed date, contradiction handling | P0 / wrong-context |
| Sensitive-fact consent | **Missing** | Clue uses granular purpose controls | Health, relationship, fertility/children, legal/financial facts require explicit consent and scoped use | P0 / legal |
| Context-used disclosure | **Partial** — structured envelope carries context used | Explainability advantage | Reader sees profile facts/chart layers used and can exclude/correct them before retry | P1 |
| Validation loop | **Built behind flag/planned** | Honest retrospective calibration can improve trust | UI for commit-before-ask probes, fatigue control, opt-out, scoring transparency, no confirmation bias | P1 / research ethics |
| Multi-domain question synthesis | **Planned** | Real questions cross career/marriage/money | Domain list in message schema, registry partial-answer rules, separate evidence, synthesis verifier | P2 / complexity |
| Provider failover | **Missing/unclear** | Commercial availability | Controlled model provider abstraction, no silent quality downgrade, consistent structured schema | P1 |
| Cost/rate limiting | **Missing/unclear** | Subscription economics | Per-entitlement quotas, token/latency budgets, abuse controls, user-visible reset and graceful limit state | P0 / commercial |
| Human astrologer escalation | **Defer** | AstroTalk validates demand | Only after credentialing, quality review, privacy, payment, records, complaints, and conflict policies | P3 / legal |

### H. Charts and practitioner workbench

| Capability | Siddha status/evidence | Benchmark signal | Next acceptance gate | Pri. / risk |
|---|---|---|---|---|
| D1 chart | **Verified/implemented** | Table stakes | Golden chart fixtures, accessible text equivalent, share/export fidelity | P0 |
| Divisional charts/vargas | **Implemented** | Cosmic Insights offers all 16+ | Validate every supported varga, labels/taps/bounds, unified chart+varga navigation | P0 |
| South/North/Eastern styles | **Implemented with defect history** | Regional expectation | Persist default everywhere, deterministic geometry, device snapshots, style parity | P0 |
| Planet tap/detail | **Implemented with historical path inconsistency** | TimePassages point-and-click benchmark | Every chart context has individual targets, keyboard semantics, same detail contract | P1 |
| Planet positions table | **Implemented** | Practitioner baseline | Sorting, pada/degree precision, horizontal overflow alternative, export | P1 |
| Vimshottari through Prana | **Implemented/partial** — backend depth and period screen; old tracker said lower levels absent | Cosmic Insights explicitly exposes Pratyantar/Sookshma/Prana | Confirm all five levels, active path, navigation, timezones, interpretation | P0 |
| Yogini dasha | **Implemented/partial interpretation** | Practitioner expectation | Full levels, effect synthesis, sources, no copied Vimshottari interpretation | P1 |
| Chara dasha/Jaimini | **Implemented/accuracy concern history** | Practitioner differentiator | Independent source audit, golden charts, convention notes, do not market until validated | P1 / wrong-results |
| Shadbala/Bhavabala/Vimshopaka | **Implemented/partial explanation** | Cosmic Insights/AstroSage depth | Explain scale, threshold, strongest/weakest meaning, domain effect, source | P1 |
| Ashtakavarga/prastara | **Implemented/partial interpretation** | Practitioner baseline | Bindus, BAV/SAV, transit use, visual explanation, calculation fixtures | P1 |
| Yogas/doshas | **Implemented with prior hardcoding/source defects** | Market expectation but trust-sensitive | Unique details per yoga, cancellation/strength, source, “flag not verdict,” no fear language | P0 / safety |
| Bhava Chalit/special lagnas/avkahada/reference | **Implemented across backend/routes** | Practitioner depth | Unified reference UX, diagrams/tables where needed, calculation provenance | P2 |
| Transit/gochara timeline | **Implemented/partial usability** | TimePassages excels at timing navigation | Past/now/future scrubber, exact windows, natal contacts, domain summary, audio | P1 |
| Solar return/Varshaphal/Tajika | **Missing or not found in mobile** | AstroSage/TimePassages offer annual techniques | Decide Vedic scope and source; do not add merely for parity | P3 / scope |
| KP/Nadi/Lal Kitab | **Defer** | AstroSage breadth | Separate convention engines would fragment trust and increase validation burden | P3 / scope |
| Practitioner profile library | **Partial** — search/filter profiles, no case folders/recents found | TimePassages/Cosmic profile scale | Tags, recents, folders, client privacy mode, bulk export/import | P2 / privacy |
| Practitioner notes linked to factors | **Partial** — basic local notes | Workbench expectation | Profile-scoped encrypted notes, links to chart/date/factor, sync/conflicts/export | P2 |

### I. Remedies, practice, and wellbeing actions

| Capability | Siddha status/evidence | Benchmark signal | Next acceptance gate | Pri. / risk |
|---|---|---|---|---|
| Profile-grounded remedies | **Implemented/partial** — remedy engine and routes | Cosmic Insights/AstroSage offer remedies | Every recommendation has trigger, evidence, tradition, cost/safety note, alternatives | P0 / safety |
| Mantra literal and 108 counter | **Implemented** | Practice feature | Correct mantra per recommendation, language/script/transliteration, pause/resume | P1 |
| Manual/auto chant mode | **Partial** — tracker UI; audio readiness varies | Ritual usability | Real audio/licensing, screen-awake/background behavior, count integrity, accessibility | P1 |
| Prayer tracking | **Implemented/partial** | Habit support | Track only meaningful repeatable practices; user chooses cadence | P2 |
| Non-trackable offering/clothing recommendations | **Implemented design direction** | Avoid gamifying one-off acts | No streak CTA; completion optional; never imply purchase required | P1 |
| Streaks | **Partial** | Wellness apps use streaks | Gentle continuity, grace days, no shame/fear, timezone-safe count, opt-out | P2 / manipulation |
| Reminders | **Partial schema, native delivery missing** | Habit loop | Local reminder first, server push optional, quiet hours, skip/snooze | P1 |
| Remedy safety and contraindication | **Partial** | Spiritual guidance can touch health/fire/fasting/cost | Risk categories, minors/pregnancy/health cautions, no medical replacement, no unsafe rituals | P0 / safety |
| Remedy expense disclosure | **Implemented in engine comments/design, UI proof needed** | Ethical differentiator | Free/low-cost option first; no affiliate sales; transparent optionality | P0 / ethics |
| Practice audio downloads | **Missing** | Headspace enables offline downloads | Licensed/audio asset management, download controls, storage/expiry | P2 |
| Personal practice library | **Partial** | Retention | Active/completed/saved practices, reason, schedule, progress, archive | P2 |

### J. Compatibility, family, reports, and sharing

| Capability | Siddha status/evidence | Benchmark signal | Next acceptance gate | Pri. / risk |
|---|---|---|---|---|
| Add prospect/profile | **Implemented** | Table stakes | Consent label, duplicate detection, unknown birth time, profile quota | P1 / privacy |
| Gun Milan summary | **Implemented** | AstroSage baseline | Calculation fixtures, cancellation/context, no reductive pass/fail | P0 / safety |
| Full compatibility interpretation | **Partial/defect history** | The Pattern Bonds and TimePassages synastry show depth demand | Domain-specific strengths/frictions, evidence, practical communication, limitations | P1 |
| Relationship timeline | **Missing** | The Pattern offers Bond timing | Only after multi-domain synthesis and memory governance; avoid deterministic relationship outcomes | P2 / safety |
| Family account | **Missing** | Headspace and Apple support family access | Account owner/member roles, billing entitlement, private profiles, no automatic cross-member visibility | P1 / privacy |
| Family profile allowance | **Missing commercial rule** | Profile scale is a common premium differentiator | Free 1, Plus 3, Pro 10, Family member-scoped allowances is a hypothesis to test, not final pricing | P1 |
| Profile-level PDF report | **Missing/partial** — share schema and some copy/share UI | AstroSage/Cosmic export PDFs | Branded PDF with conventions, generated date, sources, redaction, page QA | P1 |
| Practitioner report builder | **Missing** | Professional tools sell report depth | Select sections, notes, client-safe language, export watermark/license | P2 |
| Shareable daily/story card | **Planned schema/design** | Growth loop | Native-rendered card, no birth data by default, expiry/revoke, accessibility text | P2 / privacy |
| Data export | **Missing** | Day One makes portability core | Machine-readable JSON plus readable PDF; include memories and deletion state | P0 / privacy |

### K. Personalization, language, accessibility, and inclusion

| Capability | Siddha status/evidence | Benchmark signal | Next acceptance gate | Pri. / risk |
|---|---|---|---|---|
| Guided/Balanced/Practitioner modes | **Implemented/partial parity** | Unique Siddha advantage | Persona route/CTA/content matrix; no missing gateway; same facts across modes | P0 |
| Gentle/Direct tone | **Implemented preference, partial proof** | Useful personalization | Cross-domain tone test; safety remains unchanged | P1 |
| Language selector | **Implemented UI/preferences, coverage partial** | AstroSage supports nine Indian languages | Translation inventory, native scripts, astrology terminology glossary, fallback visibility | P1 |
| Regional formatting | **Implemented preference** | Global baseline | Dates/numbers/time, 12/24h, locale-specific calendar labels | P1 |
| RTL | **Missing** | Global readiness | Bidirectional layout/tables/charts if Arabic/Urdu enters roadmap | P3 |
| Dynamic text/font scaling | **Unverified and likely risky due custom layouts** | Accessibility baseline | 200% text, no clipping/overlap, chart legends and CTAs adapt | P0 |
| Screen reader | **Unverified** | Accessibility baseline | TalkBack/VoiceOver full critical-flow audit with meaningful chart summaries | P0 |
| Contrast/light/dark/system theme | **Implemented with repeated defect history** | Store-quality baseline | Automated contrast tokens and screenshot matrix; system bar/icon correctness | P0 |
| Reduced motion | **Implemented for splash; app-wide unknown** | Accessibility baseline | All decorative/orbit/page motion respects preference; no essential info in motion | P1 |
| Color-independent status | **Partial** | Accessibility baseline | Good/caution/avoid use icon+text, chart colors have labels/patterns | P0 |
| Voice and audio accessibility | **Partial** | Audio can broaden access | Transcript, speed, pause/resume, voice preview, pronunciation lexicon | P1 |

### L. Plans, monetization, and entitlements

| Capability | Siddha status/evidence | Benchmark signal | Next acceptance gate | Pri. / risk |
|---|---|---|---|---|
| Subscription screen | **Implemented placeholder** — purchasing intentionally disabled | CHANI/Cosmic/TimePassages use freemium | Replace with approved product matrix and transparent terms only after entitlements exist | P0 |
| StoreKit/Play Billing | **Missing** — no billing dependency found | Required for native digital subscriptions | Products, sandbox, purchase, restore, upgrade/downgrade, grace period, refunds | P0 / commercial |
| Entitlement service | **Missing** | RevenueCat models stable access as entitlements | Server-authoritative capability set, signed store events, cached offline grace | P0 / fraud |
| Feature gating | **Missing** | Tiering requires consistent enforcement | One capability registry shared by UI/API/jobs; never route-only or CSS-only gates | P0 |
| Usage metering/quotas | **Missing** | Ask/model economics require limits | Atomic per-user/profile counters, reset windows, idempotency, admin visibility | P0 |
| Restore purchases | **Missing placeholder** | App Store expectation | Restore on both platforms, account-link conflict resolution, support path | P0 |
| Billing support/cancellation | **Missing** | Commercial baseline | Manage subscription deep link, receipts, refund policy, grace/billing retry UI | P0 |
| Free tier | **Proposed** | CHANI/TimePassages keep daily/basic chart free | Today, core D1, basic calendar/panchanga, limited Ask, safety/provenance, 1 profile | P1 |
| Plus tier | **Proposed** | Main consumer subscription | Full Guided/Balanced depth, more Ask, audio/history, remedies/muhurta, 3 profiles, reports | P1 |
| Pro tier | **Proposed** | Cosmic/TimePassages monetize technical depth | Practitioner workbench, all validated techniques, advanced filters/export, higher quotas | P1 |
| Family tier | **Proposed/risk-gated** | Apple supports family sharing up to five additional members; Headspace uses six seats | Separate identities and privacy, member invitation, shared entitlement but private data | P1 / privacy |
| One-time report purchases | **Defer initially** | Common astrology monetization | Consider only after subscription value and report quality are proven | P3 |
| Paid human consultation | **Defer** | AstroTalk validates market | Separate future business with credentialing and marketplace governance | P3 / legal |
| Paywall experimentation | **Missing** | Subscription businesses optimize offers | Only after analytics consent and stable entitlements; no dark patterns or fear triggers | P2 / ethics |

#### Proposed entitlement principles, not final pricing

| Capability | Free | Plus | Pro | Family |
|---|---:|---:|---:|---:|
| Profiles | 1 | 3 | 10 | Separate member accounts + household allowance |
| Today + basic panchanga | Full | Full | Full | Full per member |
| D1 + provenance | Full | Full | Full | Full |
| Advanced vargas/strengths/reference | Preview | Balanced depth | Full practitioner depth | Based on member's entitlement |
| Ask | Small monthly allowance | Standard allowance | Higher allowance + practitioner register | Per-member allowance, never one shared transcript |
| Remedies/muhurta | Basic safe guidance | Full personal library | Full technical evidence | Private per member |
| Audio/offline downloads | Limited | Included | Included | Included |
| Exports | Basic profile export always | Consumer PDF | Advanced report builder | Private member export |
| Safety, correction, deletion, source transparency | **Always included in every plan** | **Always** | **Always** | **Always** |

This matrix needs willingness-to-pay interviews, provider-cost modeling, App
Store/Play policy review, and privacy design before becoming a product promise.
Apple's Family Sharing can extend eligible subscriptions to up to five family
members, but every family member receives their own transaction entitlement;
that does **not** justify sharing Siddha profile data or Ask history
([Apple subscription guidance](https://developer.apple.com/app-store/subscriptions/)).

### M. Privacy, safety, security, and compliance

| Capability | Siddha status/evidence | Benchmark signal | Next acceptance gate | Pri. / risk |
|---|---|---|---|---|
| Input/output safety gates | **Implemented and heavily tested** | Strong differentiator | Continuous adversarial evals, audit false positives, version rules | P0 |
| “Flag, not verdict” dosha language | **Implemented guardrails** | Ethical requirement | UI/content audits outside Ask; no paid removal framing | P0 |
| Health/legal/money/death refer-out | **Implemented** | High-stakes boundary | Regional resources, emergency language review, no diagnostic memory | P0 |
| Privacy policy and consent UI | **Partial/unclear operational coverage** | Clue demonstrates granular consent | Purpose-specific consent, providers/subprocessors, retention, model use, analytics opt-in | P0 / legal |
| Data minimization | **Partial** | OWASP says apps should access only necessary sensitive data with informed consent | Field inventory, delete unused device/profile fields, precise-location opt-in only | P0 |
| Encryption in transit | **Likely infrastructure baseline, not audited here** | Baseline | TLS config, certificate/hostname validation, no mixed content | P0 |
| Encryption at rest server | **Unverified** | Sensitive personal guidance | Database/backups/storage encryption and key-access audit | P0 |
| Encryption at rest device | **Missing for substantive caches** | OWASP MASVS storage control | Encrypted local DB and secure key storage; threat-model rooted/jailbroken limits | P0 |
| Account deletion | **Implemented UI/API/schema path, runtime proof needed** | Store/privacy baseline | Delete auth, DB, storage, caches, shares, model logs, backups policy; progress/receipt | P0 |
| Data export/access request | **Missing** | User ownership | Self-service export plus admin/legal workflow and SLA | P0 |
| Memory consent and deletion | **Missing** | Sensitive AI requirement | See profile-memory section; prohibit hidden memory | P0 |
| Audit log for admin actions | **Partial/unclear** | Admin KB and user data need accountability | Immutable publish/reject/user-access log, actor, before/after, reason | P0 |
| Admin role enforcement | **Implemented/partial** | Baseline | Server-side role checks, least privilege, MFA, session timeout, audit tests | P0 |
| Secrets management | **Partial/operational** | OWASP says never hardcode credentials | Secret Manager, rotation, no `.env` in builds, provider key health checks | P0 |
| Dependency/SBOM/vulnerability scanning | **Missing/unclear** | OWASP highlights SDK supply-chain responsibility | Dependabot/scanning, SBOM, release gate, SDK privacy review | P1 |
| Mobile penetration testing | **Missing** | Commercial sensitive-data baseline | MASVS/MASTG assessment before store launch | P0 |
| Abuse/rate limiting | **Missing/unclear** | LLM and sharing endpoints are abuse targets | User/IP/device limits, anomaly detection, prompt injection/KB exfiltration evals | P0 |
| Legal treatment of astrology claims | **Missing formal review** | Marketplace/store/regional risk | Counsel review for disclaimers, consumer protection, minors, health, remedies, subscriptions | P0 |

### N. Admin, knowledge base, RAG/OCR, and content operations

| Capability | Siddha status/evidence | Benchmark signal | Next acceptance gate | Pri. / risk |
|---|---|---|---|---|
| Admin console | **Implemented** | Internal commercial requirement | Role/device audit, operational runbook, responsive desktop QA | P1 |
| Document ingestion | **Implemented/partial** — upload/parse/review flows exist; recent publish/reject defects were fixed | Source-grounded moat | Idempotent job states, retries, virus/size/type controls, clear parse errors | P0 |
| OCR pipeline | **Partial/unclear quality system** | Classical books are often scan-heavy | Page image preservation, OCR confidence, script/language detection, manual correction | P1 |
| Structured chunk schema | **Implemented/partial** | Accurate retrieval needs semantic metadata | Page/verse/chapter/edition/translator/domain/technique/convention/quote-vs-paraphrase fields | P0 |
| Human review/publish/reject | **Implemented** | Trust requirement | Dual control for high-risk health/remedy/muhurta material, reason codes, audit trail | P0 |
| Retrieval test console | **Implemented** | RAG operations baseline | Golden queries, recall/precision set, subdomain filters, citation resolution | P0 |
| Source rights/licensing | **Missing formal register** | Commercial RAG must respect rights | Rights status, edition, allowed use, excerpt limits, removal workflow | P0 / legal |
| Citation integrity | **Implemented in Ask verifier for known refs** | Differentiator | Page/verse deep links, edition-level validation, no orphan chunks | P0 |
| KB versioning and rollback | **Partial/unclear** | Content changes can alter predictions | Immutable release, diff, staged publish, rollback, answer provenance includes KB version | P0 |
| Multilingual source alignment | **Missing** | Indian-language expansion | Original verse + transliteration + translation mapping, translator attribution | P2 |
| RAG evaluation suite | **Partial tests** | Required before scaling books | Domain recall, contradictory sources, convention conflicts, distractors, unsafe retrieval | P0 |
| Context cost/latency controls | **Partial** — kb limits and subdomain narrowing exist | Commercial model economics | Token budget, cache bundles, retrieval telemetry, no quality loss under limits | P1 |
| Prompt/agent registry admin visibility | **Implemented recent work** | Operator trust | Read-only by default; reviewed change workflow; production version display | P1 |

### O. Operations, quality, support, and growth

| Capability | Siddha status/evidence | Benchmark signal | Next acceptance gate | Pri. / risk |
|---|---|---|---|---|
| Automated unit/integration suite | **Implemented and substantial** | Strong foundation | Release-owned test matrix and flaky-test budget | P0 |
| Mobile E2E suite | **Partial** — Playwright and many screenshots; repeated manual regressions | Commercial baseline | Critical-path automation in 375x812 light/dark/personas plus native smoke | P0 |
| Device farm | **Missing** | Android fragmentation demands breadth | Firebase Test Lab/BrowserStack equivalent for nav modes, OS levels, OEMs | P1 |
| Golden astrology charts | **Partial/blocked history** | Calculation trust | Independent astrologer-approved fixtures for charts, dashas, panchanga, muhurta, festivals | P0 |
| Release checklist/signing/provenance | **Partial** — native build docs and repeated installs | Store readiness | CI artifact, checksum, version/build, changelog, rollback, staged rollout | P0 |
| Crash reporting | **Missing** | Commercial baseline | Privacy-reviewed Crashlytics/Sentry equivalent, symbolication, release tags | P0 |
| Product analytics | **Missing** | Needed for funnels/retention | Consent-aware event taxonomy; no birth/Ask text; persona/profile count only when safe | P1 / privacy |
| Feature flags/remote config | **Missing/unclear** | Safely stage risky features | Server flags by app version/platform/cohort; kill switches for Ask/domain/calendar | P0 |
| Customer support in app | **Missing/partial** | Paid users need help | Diagnostics bundle with redaction, ticket/contact, status link, restore-purchase support | P1 |
| Feedback/bug report | **Missing** | Quality loop | Screenshot/log opt-in, route/build/device metadata, redact personal content | P1 / privacy |
| App Store/Play listing readiness | **Missing/unclear** | Launch prerequisite | Screenshots, privacy labels/data safety, support/privacy URLs, subscription terms | P0 |
| Accessibility statement | **Missing** | Trust and procurement | Publish support target and known limitations after audit | P1 |
| Localization QA | **Missing** | Regional growth | Pseudolocalization, overflow screenshots, linguistic/astrological review | P1 |
| Referral/community | **Defer** | The Pattern/consumer apps use social growth | Do not add until private sharing, moderation, and core retention are proven | P3 / privacy |

## Commercial readiness gates

Siddha should not call itself launch-ready until all Gate A items pass. Later
feature breadth cannot compensate for a failed gate.

### Gate A — trustworthy private beta (P0)

- Session survives expiry, suspend/resume, process death, reboot, and network
  transitions on supported iOS/Android versions.
- Every critical mobile route respects top/bottom/keyboard safe areas and native
  back behavior.
- Today, chart, and current/adjacent calendar months render useful cached data
  immediately, with explicit stale/offline state.
- Location changes deterministically invalidate Today/calendar/festival/muhurta
  data; golden tests cover multiple countries, timezones, DST, and day boundaries.
- Profile/thread/cache isolation passes adversarial account/profile switching.
- Unknown birth time has an honest degraded product path.
- Crash reporting, API tracing, correlation IDs, and feature kill switches exist.
- Data deletion/export, device cache wipe, privacy consent, and a profile-memory
  policy are operational.
- Store billing is either completely absent from the beta or implemented with
  server-authoritative entitlements; never a decorative paywall.
- Accessibility audit passes the critical journey.

### Gate B — paid consumer launch

- Free/Plus entitlement matrix, quotas, restore, grace periods, refunds/support,
  and store webhook reconciliation are tested.
- Guided and Balanced journeys are complete and do not expose unexplained
  practitioner material.
- Ask supports configured domains with measurable quality, governed memory,
  honest unavailable states, stable thread behavior, and cost controls.
- Festival catalogue and calendar timings have an independent validation set.
- Reports/share links have redaction, expiry, revoke, and provenance.
- Product analytics can measure onboarding completion, cached load latency,
  calendar success, Ask completion, retention, and subscription conversion
  without collecting raw questions or birth details.

### Gate C — Pro/Family expansion

- Practitioner computations and sources have golden-chart sign-off.
- Pro profile library, report builder, import/export, and higher quotas are
  operational.
- Family uses separate member identities, private data stores, and per-member
  Ask/memory; shared billing never means shared private context.
- Offline downloads/sync, conflict handling, and storage controls are mature.
- Only then consider widgets, watch surfaces, community, or human consultation.

## Recommended implementation sequence

| Sequence | Workstream | Why now | Exit condition |
|---:|---|---|---|
| 1 | Reliability observability baseline | We cannot improve what we cannot measure | Crash/APM, request IDs, cache metrics, latency dashboards, kill switches |
| 2 | Native data layer and resource contract | Solves repeated tab loads, offline failure, cache leakage, and stale ambiguity at the root | Encrypted local DB; local source of truth; stale-while-revalidate; queued sync |
| 3 | Auth/lifecycle/safe-area hardening | Current reports directly damage trust | Soak/device matrix and native critical-flow automation pass |
| 4 | Location/calendar correctness | Daily timing is a core promise and wrong timings are P1 data defects | Golden location/date suite, instant month cache, explicit calculation place |
| 5 | Profile Context Ledger | Enables responsible long-term personalization | Typed facts/events, consent, confirmation, validity, edit/delete/export, audit |
| 6 | Ask quality and memory integration | Only safe after step 5 | Logical-context precheck, governed memory, dynamic prompts, configured-domain evals |
| 7 | Entitlements and plan economics | Monetization must gate stable capabilities, not unfinished screens | Store sandbox E2E, server entitlements, quotas, restore/support |
| 8 | Persona completion and accessibility | Differentiation becomes reliable instead of cosmetic | Route/content matrix and accessibility critical-flow pass |
| 9 | Reports, sharing, offline downloads | High-value Plus/Pro benefits | Redacted native share/PDF and storage controls |
| 10 | KB/RAG expansion | Depth scales after delivery and governance are trustworthy | Rights register, OCR QA, retrieval evals, KB version/rollback |

## The Profile Context Ledger: recommended data model

This is the most important new product foundation implied by the user's
examples. It should not be implemented as a free-form “memory” text blob.

| Field | Purpose |
|---|---|
| `fact_id`, `kundli_id`, `user_id` | Strict ownership and profile scope |
| `kind` | Controlled type: relationship_status, occupation_status, child, health_episode, residence, preference, life_event, etc. |
| `value` | Typed value or encrypted structured payload |
| `source` | onboarding, explicit chat statement, profile edit, imported record, operator correction |
| `source_ref` | Message/event reference so the user can see why it exists |
| `asserted_by` | profile owner, household member, practitioner, system candidate |
| `confirmation_state` | candidate, user_confirmed, disputed, revoked |
| `confidence` | Extraction confidence; never substitutes for confirmation |
| `sensitivity` | normal, relationship, health, child, legal, financial, spiritual |
| `valid_from`, `valid_to` | Temporal truth; “unwell now” must expire or be reconfirmed |
| `last_confirmed_at` | Prevent old context from silently dominating current readings |
| `allowed_domains` | Explicit scope for where the fact may be used |
| `retention_policy` | Session, 30 days, until changed, permanent-until-deleted |
| `encrypted_payload_version` | Supports key/schema rotation |
| `created_at`, `updated_at`, `deleted_at` | Audit and synchronization |

The Ask pipeline should run deterministic sanity checks before astrology:
current age and date, whether an event is already past, occupation/retirement,
relationship status, dependants, current residence, and contradictions. The
model then interprets the chart **within those constraints**. It must not use
profile context to manufacture astrological confirmation.

## Decisions to make before implementation

1. Is Siddha's first paid market primarily Guided/Balanced consumers in India,
   diaspora consumers, or Practitioner users? The same code can serve all
   three, but acquisition, onboarding, support, pricing, and validation differ.
2. Which data can be remembered by default? Recommendation: preferences and
   explicit profile edits only; conversational life facts require review and
   opt-in before durable storage.
3. Is Family a shared subscription or a shared household product?
   Recommendation: shared entitlement, separate identities and private data.
4. What is the offline promise? Recommendation for launch: profiles, D1/vargas,
   last Today, current/next calendar month, saved practices, and Ask history are
   readable; Ask generation and fresh ephemeris updates require network.
5. Which plan owns Practitioner mode? Recommendation: Pro, while basic chart
   provenance and calculation truth remain free.
6. Which languages launch? Do not expose a selector for languages without
   linguistically reviewed content and terminology.

## Source index

### Competitors and adjacent products

- [CHANI app](https://www.chani.com/app?view=home) and [free/premium feature comparison](https://chaninicholas.zendesk.com/hc/en-us/articles/1500001732421-Free-Premium-Content-In-the-App)
- [The Pattern](https://www.thepattern.com/) and [current App Store feature description](https://apps.apple.com/us/app/the-pattern-astrology/id1071085727)
- [TimePassages](https://timepassages.astrograph.com/astrology-software)
- [AstroSage Kundli](https://www.astrosage.com/mobileapps/astrosage-kundli-best-astrology-app-by-astrosage.asp)
- [Cosmic Insights](https://cosmicinsights.app/)
- [Drik Panchang settings](https://www.drikpanchang.com/settings/drikpanchang-settings.html?lang=en)
- [AstroTalk App Store listing](https://apps.apple.com/in/app/astrotalk-talk-to-astrologer/id1208433822)
- [Headspace offline downloads](https://help.headspace.com/hc/en-us/articles/115008361288-How-do-I-download-sessions-in-advance-for-offline-use) and [Family plan](https://www.headspace.com/family-plan?origin=footer)
- [Day One end-to-end encryption](https://dayoneapp.com/features/end-to-end-encryption/) and [privacy/export FAQ](https://dayoneapp.com/privacy-faqs/)
- [Clue privacy stance](https://support.helloclue.com/hc/en-us/articles/29216023055645-What-is-Clue-s-stance-on-data-privacy)

### Platform and architecture

- [Android offline-first architecture](https://developer.android.com/topic/architecture/data-layer/offline-first)
- [Android data-layer source-of-truth guidance](https://developer.android.com/topic/architecture/data-layer)
- [Apple layout and safe areas](https://developer.apple.com/design/human-interface-guidelines/layout)
- [Apple subscriptions and Family Sharing](https://developer.apple.com/app-store/subscriptions/)
- [Google Play subscription plans and offers](https://developer.android.com/google/play/billing/subscriptions)
- [RevenueCat entitlements](https://www.revenuecat.com/docs/getting-started/entitlements)
- [OWASP MASVS](https://mas.owasp.org/MASVS/) and [privacy minimization control](https://mas.owasp.org/MASVS/controls/MASVS-PRIVACY-1/)

## Repository evidence anchors

- Mobile route inventory: `ui/src/app/app.routes.ts`
- Mobile screens: `ui/src/app/features/mobile/`
- Current preference/location contract: `ui/src/app/core/preferences.service.ts`
- Current in-memory/WebView caches: `ui/src/app/core/vedic.service.ts`,
  `ui/src/app/core/festival.service.ts`, `ui/src/app/core/ask.service.ts`
- Native session behavior: `ui/src/app/core/auth.service.ts`
- Placeholder subscription: `ui/src/app/features/mobile/utility/subscription.component.ts`
- Profile/Ask/remedy/calendar/notification/cache/share schema:
  `astrospace/db/models.py`, `supabase/migrations/20260725120000_create_mobile_app_schema.sql`
- Agent registry: `astrospace/agents/registry.py`
- Existing detailed mobile trackers: `docs/mobile_screen_build_plan.md`,
  `docs/mobile_ui_regression_audit.md`, `docs/ask_full_regression_audit_2026-08-10.md`
