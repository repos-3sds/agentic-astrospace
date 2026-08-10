# Context Engine — Domain Taxonomy v2

Working spec for the Context Engine (CE) and domain agents — living document, not a
point-in-time audit; keep it current as domains ship. Each domain lists the classical
chart factors the CE must assemble before the domain agent reasons, plus the source
texts that authorize each mapping. Citation precision is deliberately chapter-level;
verse-level citations get added as the KB is digitized.

**v1 → v2 change (2026-08-10):** v1 grouped several distinct classical topics into
one combined domain per house-cluster (e.g. "Family, Home & Property" bundled
parents + siblings + land + vehicles; "Litigation, Enemies & Obstacles" bundled
formal court cases with informal rivalry). Decision, made explicit here rather than
left implicit: **split by topic, not by house.** Two reasons, not just preference —
(1) a combined domain forces one safety-review pass to cover unrelated refer-out
profiles at once (litigation's legal-outcome boundary has nothing to do with
rivalry's), which is exactly the kind of blending that hid vocabulary gaps
elsewhere in this codebase's safety work; (2) combined domains produce muddier
KB citation tagging and vaguer user-facing framing. The result is more domains,
not a bigger domain — each one stays single-topic and cheap to build with the
same playbook every domain so far has used (taxonomy entry → registry addendum →
safety extension if the topic needs one → tests → review). Splits made, and the
judgment calls involved, are called out per domain below.

Conventions: houses are whole-sign from Lagna unless noted; every domain reading is
also cross-checked from Chandra Lagna (classical practice); "Timing" is a shared
service, not a domain — every agent calls it with its own domain's houses/karakas.

Legend for engine hooks: names refer to existing payload sections produced by
`astrospace/core/vedic/` (yoga/dosha rule_ids, Jaimini karakas, vargas, dashas,
ashtakavarga_transit).

**Status column**: `built` = merged to main with a live registry addendum;
`taxonomy-only` = a `taxonomy.json` entry exists but no agent is wired up yet;
`not started` = neither exists yet, this document is the only spec.

---

## 1. Personality & Self-Understanding
**Status:** built (PR #16, `personality` in `AGENT_REGISTRY`)
**Subdomains:** core temperament, self-perception, emotional patterns,
intellect/communication style, strengths & talents, growth areas, self-awareness.

Not in v1 — added after the fact once the gap was noticed (a real astrologer
typically opens with character before any life-outcome domain). Retroactively
documented here for completeness; see `taxonomy.json`'s `personality` entry and
`registry.py`'s `_PERSONALITY_ADDENDUM` for what's actually live.

| Factor | Mapping |
|---|---|
| Houses | 1 (Lagna — primary), 3 (self-effort, courage — see Domain 3's note on the boundary), 5 (intelligence, mind) |
| Karakas | Sun (soul/ego), Moon (mind/emotions), Mercury (intellect); Jaimini: Atmakaraka (AK) |
| Vargas | D1 (whole-chart character, not divisional-chart-specific) |
| Yogas/Doshas | Pancha Mahapurusha (all five), gaja_kesari_yoga, budhaditya_yoga, kemadruma_yoga (as a growth-area flag, not a verdict), gandanta_dosha |
| Sources | BPHS (Lagna adhyaya); Uttara Kalamrita (Chandra significations); Phaladeepika, Brihat Jataka, Saravali, Raman *How to Judge a Horoscope* |
| Engine hooks | `jaimini.chara_karakas.AK`; house-1 `lord`/`lord_placement`; Pancha Mahapurusha yoga rows |
| Safety note | Explicitly not a psychological/clinical/mental-health assessment — chart-based tendencies only, never a fixed verdict on character. Has its own `_PERSONALITY_OVERCLAIM_OUTPUT` guardrail in `safety.py` for character-fatalism phrasing. |

## 2. Wealth & Finance
**Status:** built
**Subdomains:** earned income, accumulated wealth/savings, speculation/investments,
poverty combinations (daridra), fluctuating fortunes.

**Scope trimmed from v1**: 11th-house gains/income and 12th-house expenditure/loss
now belong to their own domains (15 and 16 below) — 2nd-house *accumulated*
wealth is a different question from 11th-house *income from effort* or
12th-house *loss*, and conflating them was v1's own version of the combined-domain
problem this v2 pass is fixing everywhere else.

| Factor | Mapping |
|---|---|
| Houses | 2 (dhana — primary), 5 (speculation, purva-punya), 9 (bhagya support) |
| Karakas | Jupiter (dhana karaka), Venus (luxuries), Mercury (trade), Moon (liquidity) |
| Vargas | D2 (hora — primary), D1 |
| Yogas/Doshas | dhana_yoga, lakshmi-type combinations (2nd/5th/9th lord links), chandra_mangal_yoga, daridra indicators (2nd lord in dusthana) |
| Timing | Dasha of 2nd/9th lords; Jupiter gochara over 2nd |
| Sources | BPHS (2nd house ch.; Dhana-yoga ch.); Uttara Kalamrita Kanda 4; Phaladeepika; Saravali; Raman Vol 1 (2nd house) |
| Engine hooks | `Wealth / Drive` tag; dhana_yoga rows; `vargas.D2`; `ashtakavarga.sav` for 2 |

## 3. Siblings & Self-Effort
**Status:** not started
**Subdomains:** relationship with siblings (3rd = younger, 11th = elder, per
classical convention), personal courage/initiative, short travel and
communication as extensions of self-effort.

**Judgment call**: offered as two options earlier (siblings alone, or
siblings+courage split further with courage folded into Personality). Kept as one
domain here — courage/valor and sibling relationships are not separable in the
classical 3rd house (it's literally *Parakrama sthana*, the house of effort, and
covers both); splitting them further would produce two thin domains with
overlapping natural-language questions rather than two clearly distinct ones.
Revisit if real usage shows otherwise.

| Factor | Mapping |
|---|---|
| Houses | 3 (younger siblings, courage, self-effort — primary), 11 (elder siblings) |
| Karakas | Mars (naisargika karaka for siblings and valor) |
| Vargas | D3 (drekkana — primary) |
| Yogas/Doshas | No dedicated named yoga category in this engine yet for 3rd-house strength specifically — reads house/lord strength directly until one is added |
| Timing | Dasha of 3rd lord / Mars; Mars gochara over 3rd |
| Sources | BPHS (3rd house ch.); Uttara Kalamrita Kanda 4 (3rd/11th lists); Phaladeepika |
| Engine hooks | `vargas.D3`; kartari rows on house 3 (needs a house-focused kartari extension — same gap noted for Children in v1, still open) |

## 4. Family & Parents
**Status:** not started (v1 had this combined with Property as "Family, Home & Property")
**Subdomains:** mother, father (convention-dependent house), domestic peace,
relationship with parents.

Split from v1's Domain 7 — parents/domestic-life questions and
property/asset questions are different enough in both classical sourcing and
likely user phrasing to warrant separate domains; see Domain 5 below for the
property half.

| Factor | Mapping |
|---|---|
| Houses | 4 (mother, home, domestic peace — primary), 9 (father — southern-school convention; some northern texts use 10th — **convention flag**, carried forward from v1) |
| Karakas | Moon (mother), Sun (father); Jaimini: Matrikaraka (MK), Pitrikaraka (PiK) |
| Vargas | D12 (dwadashamsha — primary, parents/lineage), D1 |
| Yogas/Doshas | sunapha/anapha/durudhara (family support around Moon), grahan_dosha on Sun (father) / Moon (mother) |
| Timing | Dasha of 4th/9th lords, Moon/Sun; Saturn gochara on 4th (kantaka shani — already modeled) |
| Sources | BPHS (4th/9th house chs.; D12 ch.); Uttara Kalamrita Kanda 4; Raman Vol 1 (4th) & Vol 2 (9th) |
| Engine hooks | `vargas.D12`; `jaimini.chara_karakas.MK/PiK`; kantaka_shani gochara rule |

## 5. Property & Assets
**Status:** not started (split from v1's Domain 7)
**Subdomains:** land/house acquisition, vehicles, ancestral property, disputes
over property (favourability framing only — actual disputes route through
Litigation/Rivals, this domain covers acquisition and ownership, not conflict).

| Factor | Mapping |
|---|---|
| Houses | 4 (land, immovable property — primary), 8 (ancestral property, inheritance), 11 (gains from property, secondary) |
| Karakas | Mars (bhumi karaka — land), Venus (vehicles, comforts), Saturn (old/ancestral property), Ketu (ancestry) |
| Vargas | D4 (chaturthamsha — primary), D16 (vehicles/comforts) |
| Yogas/Doshas | chandra_mangal_yoga (property-acquisition drive) |
| Timing | Dasha of 4th lord / Mars, for purchase timing; Saturn gochara on 4th (kantaka shani) |
| Sources | BPHS (4th house ch.; D4 ch.); Uttara Kalamrita Kanda 4; Raman Vol 1 (4th) |
| Engine hooks | `vargas.D4/D16`; kantaka_shani gochara rule; `arudha_padas` A4 |

## 6. Education & Intellect
**Status:** taxonomy-only (`education` in `taxonomy.json`, unbuilt)
**Subdomains:** basic education, higher education/degrees, field of study, breaks
in education, competitive exams, memory/intelligence quality, scholarship/research.

Unchanged from v1 — already single-topic, no split needed. Note the boundary with
Domain 13 (Foreign): "should I study abroad" is Education-primary /
Foreign-secondary, same multi-domain pattern the router already supports.

| Factor | Mapping |
|---|---|
| Houses | 4 (basic education, mother's nurture), 5 (intelligence, purva-punya), 9 (higher wisdom, university), 2 (speech, early learning) |
| Karakas | Mercury (buddhi), Jupiter (jnana/wisdom), Venus (arts), Moon (mind/receptivity) |
| Vargas | D24 (chaturvimshamsha — primary), D1, D9 |
| Yogas/Doshas | saraswati_yoga, budhaditya_yoga, `Learning / Wisdom` & `Intellect / Status` tagged yogas, guru_chandala (corrupted guidance) |
| Timing | Dasha of 4th/5th/9th lords & Mercury/Jupiter; Jupiter gochara on 5th/9th |
| Sources | BPHS (4th/5th house chs.); Uttara Kalamrita Kanda 4; Jataka Parijata (vidya); K.N. Rao *Planets & Education*; Raman Vol 1 (4th/5th) |
| Engine hooks | saraswati_yoga, budhaditya_yoga rows; `vargas.D24`; `shadbala.classical` Mercury/Jupiter |

## 7. Children & Progeny
**Status:** built
**Subdomains:** timing of childbirth, delay/denial (anapatya), children's
wellbeing, relationship with children, adoption indicators. Number/gender
tendencies flagged low-confidence — see convention flags below.

Unchanged from v1.

| Factor | Mapping |
|---|---|
| Houses | 5 (primary), 9 (5th-from-5th), 11 (5th-from-7th: spouse's progeny view) |
| Karakas | Jupiter (putrakaraka naisargika); Jaimini: Putrakaraka (PK) |
| Vargas | D7 (saptamamsha — primary), D1, D9 |
| Yogas/Doshas | papa_kartari on 5th, grahan/gandanta afflicting 5th lord or Jupiter |
| Timing | Dasha of 5th lord / Jupiter / PK; Jupiter gochara on 5th/9th |
| Sources | BPHS (5th-house ch.); Uttara Kalamrita Kanda 4; Phaladeepika; Prasna Marga (santana prasna); Raman Vol 1 (5th) |
| Engine hooks | `vargas.D7`; `jaimini.chara_karakas.PK`; kartari rows on house 5 |

## 8. Health & Longevity
**Status:** built
**Subdomains:** constitution/vitality, chronic vs acute disease, disease
location, mental health framing, accidents/surgery, recovery windows.
Longevity/death prediction stays explicitly out of scope — non-negotiable, not a
scope choice.

Unchanged from v1.

| Factor | Mapping |
|---|---|
| Houses | 1 (body/vitality), 6 (roga), 8 (chronic — reference only, never lifespan), 12 (hospitalization) |
| Karakas | Sun (vitality), Moon (mind/fluids), Saturn (chronic), Mars (accidents/surgery), Mercury (nerves/skin) |
| Vargas | D6 (shashthamsha — VERIFY-flagged in engine), D30 (trimshamsha), D1 |
| Yogas/Doshas | grahan_dosha, gandanta (Moon), kemadruma (mental, as a flag), combustion & debilitation of lagna lord |
| Sources | BPHS (6th/8th house chs.; ref. only); Uttara Kalamrita Kanda 4; Phaladeepika; Prasna Marga (disease prasna); Raman Vol 1 (6th) |
| Engine hooks | `Caution / Affliction` tags; `planetary_conditions`; `shadbala.classical.sufficient`; sade_sati payload |

## 9. Marriage & Relationships
**Status:** built
**Subdomains:** timing of marriage, spouse nature, marital harmony & discord,
compatibility, delay/denial, second marriage, divorce/separation, in-laws.

**Scope trimmed from v1**: business/trade partnerships (the 7th house's other
signification) now belong to Domain 10 — a question about a spouse and a
question about a business partner warrant separate framing even though both are
7th-house.

| Factor | Mapping |
|---|---|
| Houses | 7 (primary), 2 (family life), 4 (domestic happiness), 8 (mangalya/longevity of union), 5 (romance) |
| Karakas | Venus (kalatra karaka), Jupiter (husband, female charts), Mars (Kuja dosha axis); Jaimini: Darakaraka, Upapada Lagna |
| Vargas | D9 (navamsha — primary), D1 |
| Yogas/Doshas | manglik_dosha (+ exceptions/net_severity), gandanta_dosha, grahan_dosha on Venus/7th lord, papa_kartari on 7th, gun_milan |
| Timing | Dasha of 7th lord / Venus / Darakaraka; Jupiter gochara on 7th & Upapada |
| Sources | BPHS (7th-house ch.; Upapada ch.); Uttara Kalamrita Kanda 4; Phaladeepika; Jataka Parijata; Muhurta Chintamani; Raman Vol 2 |
| Engine hooks | `Marriage / Caution` tag; `doshas.manglik/gandanta/grahan`; `compatibility.gun_milan`; `jaimini.upapada`, `chara_karakas.DK`; `vargas.D9` |

## 10. Business Partnerships
**Status:** not started
**Subdomains:** trade/commercial partnerships, joint ventures, professional
collaboration (boundary with Career: a partnership question is this domain, a
promotion/job question is Career even when the 10th house overlaps).

Split from v1's Marriage domain — new, not previously separately spec'd.

| Factor | Mapping |
|---|---|
| Houses | 7 (trade/business partnerships — primary), 3 (self-initiated ventures) |
| Karakas | Mercury (trade/commerce), Venus (partnership harmony) |
| Vargas | D9 (inner partnership strength), D1 |
| Timing | Dasha of 7th lord / Mercury; Jupiter gochara on 7th |
| Sources | BPHS (7th house ch.); Uttara Kalamrita Kanda 4; Prasna Marga (partnership prasna) |
| Engine hooks | `vargas.D9`; `jaimini.upapada` (secondary — Upapada's primary home is Marriage) |

## 11. Rivals & Disputes
**Status:** not started (split from v1's Domain 10)
**Subdomains:** open enemies/competitors, hidden/secret opposition, interpersonal
conflict short of formal legal proceedings. Boundary with Domain 12: this domain
is favourability/timing for a rivalry, not a legal-outcome prediction.

| Factor | Mapping |
|---|---|
| Houses | 6 (open enemies — primary), 12 (hidden/secret enemies) |
| Karakas | Mars (conflict), Saturn (persistent rivalry), Rahu (deception) |
| Vargas | D6, D1 |
| Yogas/Doshas | papa_kartari on 6th/lagna, `Caution / Affliction` tags |
| Timing | Dasha of 6th lord; Mars gochara triggers (mars_moon_trigger rule, already modeled) |
| Sources | Prasna Marga (rivalry/dispute prasna); BPHS (6th house ch.) |
| Engine hooks | gochara mars trigger; `shadbala.classical` comparative strength |

## 12. Litigation & Court Cases
**Status:** taxonomy-only (`litigation` in `taxonomy.json`, unbuilt)
**Subdomains:** court cases, formal legal proceedings, victory/defeat assessment,
imprisonment indicators.

Narrowed from v1's Domain 10 — this is now specifically the formal-legal-process
half; informal rivalry moved to Domain 11. **Safety note, carried forward and
sharpened**: this domain sits directly on the "legal" refer-out boundary already
built in `safety.py` — outcome-directive questions ("will I win my case") refer
out per the existing legal-cluster patterns; timing/favourability questions
("is this a good time to pursue my case") stay answerable, same distinction the
money and immigration clusters already rest on. Advisory tone only, no
deterministic verdicts.

| Factor | Mapping |
|---|---|
| Houses | 6 (ripu, litigation — primary), 7 (the opponent, prasna method), 11 (victory as 6th-from-6th) |
| Karakas | Saturn (delay/legal process), Mars (aggressive litigation), Mercury (documentation/contracts); Jaimini: Gnatikaraka (GK) |
| Vargas | D6, D1 |
| Yogas/Doshas | viparita_raja_yoga (harsha — 6th-lord reversals favour the native), papa_kartari |
| Timing | Dasha of 6th lord vs 7th lord strength comparison (prasna method); Mars/Saturn gochara triggers |
| Sources | Prasna Marga (litigation prasna — primary); BPHS (6th house ch.); Uttara Kalamrita Kanda 4; Raman Vol 1 (6th) |
| Engine hooks | viparita_raja_yoga rows; `jaimini.chara_karakas.GK`; `shadbala.classical` comparative strength |

## 13. Foreign Travel & Settlement
**Status:** built
**Subdomains:** short travel, foreign residence, emigration, gains/losses abroad,
return home, education abroad.

Unchanged from v1.

| Factor | Mapping |
|---|---|
| Houses | 12 (foreign residence — primary), 9 (long journeys), 3 (short journeys), 7 (residence away from birthplace) |
| Karakas | Rahu (primary), Moon, Venus, Mercury |
| Yogas/Doshas | Rahu association with 12th/9th lords; `Caution / Karmic` Rahu tags |
| Timing | Dasha of 12th/9th lords or Rahu; Rahu-Ketu gochara over 4th/12th axis |
| Sources | BPHS (9th/12th chs.); Uttara Kalamrita Kanda 4; Prasna Marga (travel prasna) |
| Engine hooks | gochara Rahu/Ketu caution rules; `arudha_padas` A12 |
| Safety note | Visa/immigration-outcome questions are a real-world legal process, not astrology — gated by `safety.py`'s immigration cluster (5 review rounds); timing/favourability stays answerable. |

## 14. Spirituality, Dharma & Fortune
**Status:** taxonomy-only (`spirituality` in `taxonomy.json`, unbuilt; renamed
here from v1's "Spirituality & Moksha" to make an absorbed scope explicit)
**Subdomains:** spiritual inclination, guru/lineage connection, meditation/sadhana
aptitude, renunciation combinations, general fortune/purva-punya questions.

**Judgment call**: "general fortune/luck" was considered as its own domain
(9th-house bhagya, independent of spiritual practice) but folded in here instead
— in practice a "how's my fortune" question is rarely asked in isolation; it's
almost always attached to a specific life-area ("will I be lucky in my career")
that already resolves to that area's own domain with 9th-house bhagya as
supporting evidence, not a standalone one. A thin "Fortune" domain would have
weak, hard-to-differentiate user intent against the domains it would sit next to.

| Factor | Mapping |
|---|---|
| Houses | 12 (moksha), 9 (dharma, guru, general fortune), 5 (purva-punya), 8 (occult depth) |
| Karakas | Ketu (moksha karaka), Jupiter (guru), Saturn (vairagya); Jaimini: Atmakaraka, Karakamsha |
| Vargas | D20 (vimshamsha — primary), D9, D60 |
| Yogas/Doshas | `Caution / Karmic` tags, guru_chandala, kemadruma reinterpreted (detachment) |
| Timing | Dasha of Ketu/12th lord/AK; Ketu gochara |
| Sources | BPHS (Karakamsha ch.); Jaimini Sutras; Uttara Kalamrita; Phaladeepika; Sanjay Rath's Jaimini commentaries |
| Engine hooks | `jaimini.chara_karakas.AK`; `vargas.D20/D60`; guru_chandala row; gochara Ketu rules |

## 15. Gains, Income & Social Circle
**Status:** not started
**Subdomains:** income from effort (distinct from 2nd-house accumulated wealth),
windfalls, fulfillment of desires, elder siblings, friendships/social network.

**Judgment call**: "social circle/friendships" was considered as a separate
domain but folded in here — both are 11th-house significations and a standalone
friendships domain would have thin, overlapping natural-language questions
against this one ("will I make good friends" and "will my income grow" both
route through 11th-house strength). No dedicated divisional chart exists for the
11th house in the standard shodashavarga system — it's read from D1 and D9, not
a dedicated varga, noted explicitly so this isn't mistaken for an oversight.

| Factor | Mapping |
|---|---|
| Houses | 11 (income, gains, fulfillment of desires, elder siblings, friendships — primary) |
| Karakas | Jupiter (gains karaka, shared with Wealth), Saturn (elder siblings, per some schools) |
| Vargas | D1, D9 — no dedicated 11th-house divisional chart in the standard 16-varga system |
| Yogas/Doshas | dhana_yoga variants tied to 11th lord, Labha-related combinations |
| Timing | Dasha of 11th lord / Jupiter; Jupiter gochara on 11th |
| Sources | BPHS (11th house ch.); Uttara Kalamrita Kanda 4 (11th list); Raman Vol 2 (11th) |
| Engine hooks | `ashtakavarga.sav` for 11 |

## 16. Expenses & Losses
**Status:** not started
**Subdomains:** expenditure, wastage, financial drain. Explicitly does not cover
hospitalization (stays in Health's scope) or moksha/foreign-residence (stays in
Spirituality's/Foreign's scope) — this domain is specifically the
expenses/loss reading of the 12th house, not every 12th-house topic at once,
which is exactly the kind of over-bundling this v2 pass is trying to avoid.

| Factor | Mapping |
|---|---|
| Houses | 12 (expenditure, loss, wastage — primary) |
| Karakas | Saturn (chronic drain), Rahu/Ketu (sudden unexplained loss) |
| Vargas | D1 |
| Yogas/Doshas | papa_kartari on 2nd/11th (wealth-draining patterns), 12th lord affliction |
| Timing | Dasha of 12th lord; Saturn/Rahu gochara on 12th or 2nd |
| Sources | BPHS (12th house ch.); Uttara Kalamrita Kanda 4 (12th list) |
| Engine hooks | none dedicated yet — needs a 12th-house-focused kartari/affliction extension, same class of gap already open for Siblings (Domain 3) |

## Excluded — not a domain, by policy

**8th house (Randhra/Ayur) — Longevity & Crisis.** Deliberately not a domain,
regardless of the granularity direction taken above. This is the death/lifespan
house; CLAUDE.md's non-negotiable (no death, longevity, or medical/legal/
financial verdicts) makes this a hard product/safety boundary, not a scope
choice that "make it bigger" reopens. Chronic-health framing already reaches the
8th house *within* Health & Longevity's scope (reference only, never lifespan);
inheritance reaches it within Property & Assets. Nothing about splitting domains
elsewhere changes this exclusion.

---

## Cross-cutting services (not domains)

**Timing service** — every agent calls with (domain houses, domain karakas):
active Vimshottari chain (5 levels) + Yogini cross-check + gochara rules with
vedha + ashtakavarga_transit support + dasha-lord dignity from shadbala.classical.

**Chart-strength service** — dignity, shadbala sufficiency, combustion/war/avastha
for any planet the domain agent focuses on.

**Remedial layer (later)** — gems/metals/days already in `favourable`; classical
remedial texts are a separate KB phase.

## Router mapping (question → domain)

Prasna Marga's query classification is the classical authority for mapping
question types to bhavas; the router = keyword/LLM classification against the
domain descriptions above + keyword fallbacks. With 16 domains instead of 10,
multi-domain questions get *more* common, not less — a question like "will I get
along with my business partner" now spans Domain 10 (Business Partnerships,
primary) and Domain 3 (Siblings & Self-Effort, if the partner is also family) —
the CE already supports multi-domain context assembly from day one; this split
leans on that harder than v1 did, not around it.

## Known convention flags to resolve against the reference corpus

1. Father = 9th vs 10th house (school split) — now lives in Domain 4 (Family & Parents)
2. Number/gender of children — low-confidence, consider excluding from product
3. Longevity/death predictions — excluded by policy regardless of classical basis (see the explicit exclusion above)
4. D6 varga rule is VERIFY-flagged in the engine (Health domain depends on it)
5. Imprisonment/litigation outcomes — advisory tone, no deterministic verdicts (Domain 12)
6. 3rd vs 11th house for younger/elder siblings — standard convention, not disputed, but both houses now feed one domain (3) so the split matters less in practice than it did across two houses in different v1 domains
7. No dedicated divisional chart (varga) for the 11th house in the standard shodashavarga system — Domain 15 reads from D1/D9 only; not an engine gap, a fact about the classical system

## Ground-truth validation against BPHS (2026-08-10)

A source-cited validation pass checked the engine's actual computation
functions against BPHS directly, not against this document's own prior
claims — see `tests/test_bphs_ground_truth.py` for the permanent, CI-enforced
version of this check. Any new domain agent whose addendum references one of
these techniques should cite this section rather than re-deriving from
scratch.

**Confirmed correct, exact match** (used by Domains 1, 2, 7, 9, 12 among
others): Special Ascendants (Bhava/Hora/Ghati Lagna, `special_lagnas.py`),
Drishti Bala aspectual strength (`strength.sputa_drishti`, all 8 classical
piecewise segments plus the Mars/Jupiter/Saturn special-aspect overrides),
planetary relationships (`strength.NATURAL_RELATIONS`, `temporal_relation`,
`panchadha_relation` — natural + temporal → the 5-fold Great Friend/Friend/
Neutral/Enemy/Great Enemy compound).

**Confirmed gaps, not built** (a validation pass found them; building them
is separate work, not done as part of this pass):
1. **Kalapurusha sign-to-body-part mapping** — no engine reference anywhere;
   relevant to Health & Longevity's "disease location by body part"
   subdomain, currently unsupported. Only the unrelated Rajju
   (nakshatra-based) system exists, in `compatibility.py`.
2. **D-60 (Shashtyamsha) deity database** — the engine computes the D-60
   *sign* correctly (`vargas.d60()`) but has no deity-name layer (60 named
   deities, odd/even sign reversal rule) on top of it. Relevant to any
   domain that wants Shashtyamsha-level "finest analysis" framing.
3. **Shayanadi Avastha** — the 12-state modulo-12 formula (distinct from
   the Baladi and Cheshta avastha systems the engine already has). Lower
   priority: BPHS itself frames this as modifying dasha timing/intensity,
   not core house significations, so no domain currently depends on it.

**A meta-finding worth keeping in mind for any future source-extraction
pass**: not every section of an AI-synthesized "validation" document is
equally trustworthy just because it cites a chapter. The Vimshopaka Bala
per-varga weight table in the document that drove this pass claimed each of
its 4 schemes summed to 20.0, but 3 of the 4 actually summed to 21.0, 16.5,
and 8.0 when checked by hand — an internal inconsistency that means that
specific table cannot be a faithful transcription, regardless of its
citation. This codebase's own `vimshopaka.py` weights (self-consistent, each
scheme correctly totals 20, already documented as "the commonly-published
Vimshopaka table") were deliberately NOT changed on the strength of a
document that fails its own arithmetic. Lesson: check that a claimed table
actually sums to its claimed total before trusting any of its individual
values — this is now standard practice for any future extraction pass, not
a one-off catch.
