# Context Engine — Domain Taxonomy v1

Working spec for the Context Engine (CE) and domain agents. Each domain lists the
classical chart factors the CE must assemble before the domain agent reasons, plus
the source texts that authorize each mapping. Citation precision is deliberately
chapter-level; verse-level citations get added as the KB is digitized.

Conventions: houses are whole-sign from Lagna unless noted; every domain reading is
also cross-checked from Chandra Lagna (classical practice); "Timing" is a shared
service, not a domain — every agent calls it with its own domain's houses/karakas.

Legend for engine hooks: names refer to existing payload sections produced by
`astrospace/core/vedic/` (yoga/dosha rule_ids, Jaimini karakas, vargas, dashas,
ashtakavarga_transit).

---

## 1. Career & Profession
**Subdomains:** job vs business, promotions/authority, career field selection,
job change/instability, unemployment spells, government/politics, fame & status,
professional reputation.

| Factor | Mapping |
|---|---|
| Houses | 10 (karma), 6 (service/employment), 7 (business/partnerships), 2 & 11 (income from career), 5 (authority/politics), 3 (self-effort, media) |
| Karakas | Sun (authority, government), Saturn (service, labour), Mercury (commerce), Jupiter (counsel/advisory roles); Jaimini: Amatyakaraka |
| Vargas | D10 (dashamsha — primary), D1, D9 (inner strength of career planets) |
| Yogas/Doshas | raja_yoga, viparita_raja_yoga, Pancha Mahapurusha (all five), budhaditya_yoga, amala_yoga (10th from Moon/Lagna), dhana_yoga (income houses) |
| Timing | Dasha of 10th lord / planets in 10th / Amatyakaraka; Saturn & Jupiter gochara over 10th house and 10th lord; ashtakavarga of the 10th |
| Sources | BPHS (10th-house judgement ch.; karakatva ch.); Uttara Kalamrita Kanda 4 (10th-bhava list) & Kanda 5 (Sun/Saturn karakatvas); Phaladeepika (bhava chapters); B.V. Raman *How to Judge a Horoscope* Vol 2 (10th house); K.N. Rao *Ups & Downs in Career*; Sanjay Rath *Timing of Events* |
| Engine hooks | `Power / Career`, `Reputation / Career` yoga tags; `jaimini.chara_karakas.AmK`; `vargas.D10`; `shadbala.classical` for Sun/Saturn/10th lord; `ashtakavarga_transit` |

## 2. Wealth & Finance
**Subdomains:** earned income, accumulated wealth/savings, speculation/investments,
inheritance & sudden gains, debts & losses, property as asset (overlaps Domain 7),
poverty combinations (daridra), fluctuating fortunes.

| Factor | Mapping |
|---|---|
| Houses | 2 (dhana), 11 (labha), 5 (speculation, purva-punya), 9 (bhagya/fortune), 8 (inheritance, others' money), 12 (expenditure/loss), 6 (debts) |
| Karakas | Jupiter (dhana karaka), Venus (luxuries), Mercury (trade), Moon (liquidity) |
| Vargas | D2 (hora — primary), D4 (fixed assets), D1 |
| Yogas/Doshas | dhana_yoga, lakshmi-type combinations (2nd/5th/9th/11th lord links), chandra_mangal_yoga, daridra indicators (2nd/11th lords in dusthana), kemadruma_yoga (poverty-of-mind classical result) |
| Timing | Dasha of 2nd/11th/9th lords; Jupiter gochara over 2nd/11th; ashtakavarga bindus of 2nd & 11th |
| Sources | BPHS (2nd & 11th house chs.; Dhana-yoga ch.); Uttara Kalamrita Kanda 4 (2nd/11th lists); Phaladeepika; Saravali (planet wealth significations); Raman Vol 1 (2nd house) & Vol 2 (11th) |
| Engine hooks | `Wealth / Drive` tag; dhana_yoga rows; `vargas.D2`; `ashtakavarga.sav` for 2/11; `masa`/panchanga for muhurta-side queries |

## 3. Marriage & Relationships
**Subdomains:** timing of marriage, spouse nature/direction, marital harmony &
discord, compatibility (melapak), delay/denial combinations, second marriage,
divorce/separation, love vs arranged, in-laws.

| Factor | Mapping |
|---|---|
| Houses | 7 (primary), 2 (family life), 4 (domestic happiness), 8 (mangalya/longevity of union), 12 (bed comforts), 5 (romance) |
| Karakas | Venus (kalatra karaka for all; spouse for men), Jupiter (husband, in female charts), Mars (Kuja dosha axis); Jaimini: Darakaraka, Upapada Lagna |
| Vargas | D9 (navamsha — primary; spouse & inner marriage), D1 |
| Yogas/Doshas | manglik_dosha (+ exceptions/net_severity), gandanta_dosha, grahan_dosha on Venus/7th lord, papa_kartari on 7th, gun_milan (full ashta-koota) |
| Timing | Dasha of 7th lord / Venus / Darakaraka; Jupiter gochara on 7th & Upapada; navamsha dasha correlations |
| Sources | BPHS (7th-house ch.; Upapada ch.); Uttara Kalamrita Kanda 4 (7th list); Phaladeepika (kalatra bhava); Jataka Parijata (strī/dāra chapters); Muhurta Chintamani (melapak tables — already the basis of `compatibility.py`); Raman Vol 2 (7th house); K.N. Rao school marriage-timing monographs |
| Engine hooks | `Marriage / Caution` tag; `doshas.manglik/gandanta/grahan`; `compatibility.gun_milan`; `jaimini.upapada`, `chara_karakas.DK`; `vargas.D9` + vargottama flags |

## 4. Health & Longevity
**Subdomains:** constitution/vitality, chronic vs acute disease, disease location
(body-part by house/sign), mental health, accidents/surgery, longevity band
(ayurdaya), recovery windows, hospitalization.

| Factor | Mapping |
|---|---|
| Houses | 1 (body/vitality), 6 (roga), 8 (chronic/ayus), 12 (hospitalization), 3 (longevity supplement); body-part mapping via kalapurusha signs |
| Karakas | Sun (vitality), Moon (mind/fluids), Saturn (chronic), Mars (accidents/surgery, blood), Mercury (nerves/skin) |
| Vargas | D6 (shashthamsha — NOTE: rule is VERIFY-flagged in engine), D30 (trimshamsha — misfortunes), D1, D3 (drekkana for body parts) |
| Yogas/Doshas | grahan_dosha, gandanta (Moon), kemadruma (mental), combustion & debilitation of lagna lord, papa_kartari on lagna |
| Timing | Dasha of 6th/8th/22nd-drekkana lords; Sade Sati phases (already modeled); maraka dashas (2nd/7th lords) for longevity questions — LONGEVITY PREDICTION ITSELF IS OUT OF SCOPE for the product (classical ethics + product safety: no death predictions) |
| Sources | BPHS (6th/8th house chs.; Ayurdaya ch. — reference only); Uttara Kalamrita Kanda 4; Phaladeepika (roga chapters); Prasna Marga (disease prasna — strongest classical source on health queries); Raman Vol 1 (6th) |
| Engine hooks | `Caution / Affliction` tags; `planetary_conditions` (combustion/avastha/war); `shadbala.classical.sufficient`; `doshas.gandanta`; sade_sati payload |

## 5. Education & Intellect
**Subdomains:** basic education, higher education/degrees, field of study, breaks
in education, competitive exams, memory/intelligence quality, foreign education
(overlaps Domain 8), scholarship/research.

| Factor | Mapping |
|---|---|
| Houses | 4 (basic education, mother's nurture), 5 (intelligence, purva-punya), 9 (higher wisdom, university), 2 (speech, early learning), 3 (courage in exams) |
| Karakas | Mercury (buddhi), Jupiter (jnana/wisdom), Venus (arts), Moon (mind/receptivity) |
| Vargas | D24 (chaturvimshamsha — primary), D1, D9 |
| Yogas/Doshas | saraswati_yoga, budhaditya_yoga, `Learning / Wisdom` & `Intellect / Status` tagged yogas, guru_chandala (corrupted guidance), grahan on Mercury/Jupiter |
| Timing | Dasha of 4th/5th/9th lords & Mercury/Jupiter; Jupiter gochara on 5th/9th |
| Sources | BPHS (4th/5th house chs.); Uttara Kalamrita Kanda 4; Jataka Parijata (vidya); K.N. Rao *Planets & Education*; Raman Vol 1 (4th/5th) |
| Engine hooks | saraswati_yoga, budhaditya_yoga rows; `vargas.D24`; `shadbala.classical` Mercury/Jupiter |

## 6. Children & Progeny
**Subdomains:** timing of childbirth, delay/denial (anapatya), number/gender
tendencies (flag: convention-heavy, low-confidence), children's wellbeing,
relationship with children, adoption indicators.

| Factor | Mapping |
|---|---|
| Houses | 5 (primary), 9 (5th-from-5th), 2 (family growth), 11 (5th-from-7th: spouse's progeny view) |
| Karakas | Jupiter (putrakaraka naisargika); Jaimini: Putrakaraka (PK) |
| Vargas | D7 (saptamamsha — primary), D1, D9 |
| Yogas/Doshas | papa_kartari on 5th, grahan/gandanta afflicting 5th lord or Jupiter, sarpa/pitra-type afflictions (Rahu-Ketu axis on 5th — pitra dosha still a KB gap) |
| Timing | Dasha of 5th lord / Jupiter / PK; Jupiter gochara on 5th/9th |
| Sources | BPHS (5th-house ch.; Santana yoga discussions); Uttara Kalamrita Kanda 4; Phaladeepika; Prasna Marga (santana prasna); Raman Vol 1 (5th) |
| Engine hooks | `vargas.D7`; `jaimini.chara_karakas.PK`; kartari rows on house 5 (needs a house-focused kartari extension — currently lagna/Moon anchored) |

## 7. Family, Home & Property
**Subdomains:** parents (mother 4th, father 9th/10th by school — flag convention),
siblings (3rd/11th), domestic peace, land/house acquisition, vehicles, relocation,
ancestral property, disputes over property.

| Factor | Mapping |
|---|---|
| Houses | 4 (mother, home, land, vehicles), 9 (father — southern convention; 10th in some northern texts — CONVENTION FLAG), 3 (younger siblings), 11 (elder siblings), 2 (kutumba/family), 8 (ancestral/inheritance) |
| Karakas | Moon (mother), Sun (father), Mars (siblings, land — bhumi karaka), Venus (vehicles, comforts), Ketu (ancestry); Jaimini: Matrikaraka, Pitrikaraka, Bhratrikaraka |
| Vargas | D4 (chaturthamsha — property), D12 (dwadashamsha — parents/lineage), D3 (drekkana — siblings), D16 (vehicles/comforts) |
| Yogas/Doshas | `Ancestral / Caution` tags, chandra_mangal (property drive), sunapha/anapha/durudhara (family support around Moon), grahan on Sun (father) / Moon (mother) |
| Timing | Dasha of 4th lord/Mars for property purchase; Saturn gochara on 4th (kantaka shani — already modeled) |
| Sources | BPHS (3rd/4th/9th house chs.; D12 ch.); Uttara Kalamrita Kanda 4; Phaladeepika; Raman Vol 1 (3rd/4th) & Vol 2 (9th) |
| Engine hooks | `vargas.D4/D12/D3/D16`; `jaimini.chara_karakas.MK/PiK/BK`; kantaka_shani gochara rule; `arudha_padas` A4 |

## 8. Foreign Travel & Settlement
**Subdomains:** short travel, long foreign residence, permanent settlement/
emigration, gains abroad vs losses abroad, return to homeland, education abroad.

| Factor | Mapping |
|---|---|
| Houses | 12 (foreign residence, videsha), 9 (long journeys), 3 (short journeys), 7 (residence away from birthplace), 4 afflicted (away from homeland) |
| Karakas | Rahu (foreign, unconventional), Moon (movement, chara signs), Venus/Mercury (travel comfort/trade) |
| Vargas | D1, D9; chara/sthira sign balance of 12th/4th lords |
| Yogas/Doshas | Rahu association with 12th/9th lords; chara rashi emphasis; `Caution / Karmic` Rahu tags |
| Timing | Dasha of 12th/9th lords or Rahu; Rahu-Ketu gochara over 4th/12th axis |
| Sources | BPHS (9th/12th chs.); Uttara Kalamrita Kanda 4 (12th list); Prasna Marga (travel prasna); modern: K.N. Rao school foreign-travel monographs |
| Engine hooks | gochara Rahu/Ketu caution rules; `SIGN_MODALITY` (chara emphasis); `arudha_padas` A12 |

## 9. Spirituality & Moksha
**Subdomains:** spiritual inclination vs ritualism, guru/lineage connection,
meditation/sadhana aptitude, renunciation combos (sanyasa), moksha indicators,
karmic debts (Rahu-Ketu axis reading).

| Factor | Mapping |
|---|---|
| Houses | 12 (moksha), 9 (dharma, guru), 5 (mantra, purva-punya), 8 (occult depth), 4 (inner peace) |
| Karakas | Ketu (moksha karaka), Jupiter (guru), Saturn (vairagya); Jaimini: Atmakaraka (soul's direction — primary), Karakamsha (AK's navamsha sign) |
| Vargas | D20 (vimshamsha — primary), D9 (dharma), D60 |
| Yogas/Doshas | `Caution / Karmic` tags, guru_chandala (guru-lineage corruption), sanyasa combinations (4+ planets in one sign — KB gap, not yet a rule), kemadruma reinterpreted (detachment) |
| Timing | Dasha of Ketu/12th lord/AK; Ketu gochara; Saturn dasha maturity phases |
| Sources | BPHS (Karakamsha ch.); Jaimini Sutras (Atmakaraka/Karakamsha); Uttara Kalamrita; Phaladeepika (pravrajya yogas); Sanjay Rath's Jaimini commentaries |
| Engine hooks | `jaimini.chara_karakas.AK`; `vargas.D20/D60`; guru_chandala row; gochara Ketu rules |

## 10. Litigation, Enemies & Obstacles
**Subdomains:** court cases, open enemies/rivals, hidden enemies (12th), theft/
loss, service disputes, victory/defeat assessment, imprisonment indicators
(flag: sensitive — advisory tone only).

| Factor | Mapping |
|---|---|
| Houses | 6 (ripu, litigation — primary), 8 (hidden obstruction), 12 (secret enemies, confinement), 7 (the opponent in prasna), 11 (victory as 6th-from-6th) |
| Karakas | Mars (conflict), Saturn (delay/confinement), Rahu (deception); Jaimini: Gnatikaraka (GK — rivals/kinsmen strife) |
| Vargas | D6, D1 |
| Yogas/Doshas | viparita_raja_yoga (harsha — 6th-lord reversals favor the native), papa_kartari, `Caution / Affliction` tags |
| Timing | Dasha of 6th lord vs 7th lord strength comparison (prasna method); Mars/Saturn gochara triggers (mars_moon_trigger rule already modeled) |
| Sources | Prasna Marga (litigation prasna — primary); BPHS (6th house ch.); Uttara Kalamrita Kanda 4 (6th list); Raman Vol 1 (6th) |
| Engine hooks | viparita_raja_yoga rows; `jaimini.chara_karakas.GK`; gochara mars trigger; `shadbala.classical` comparative strength |

---

## Cross-cutting services (not domains)

**Timing service** — every agent calls with (domain houses, domain karakas):
active Vimshottari chain (now 5 levels) + Yogini cross-check + gochara rules with
vedha + ashtakavarga_transit support + dasha-lord dignity from shadbala.classical.

**Chart-strength service** — dignity, shadbala sufficiency, combustion/war/avastha
for any planet the domain agent focuses on.

**Remedial layer (later)** — gems/metals/days already in `favourable`; classical
remedial texts are a separate KB phase.

## Router mapping (question → domain)
Prasna Marga's query classification is the classical authority for mapping
question types to bhavas; v1 router = LLM classification against the 10 domain
descriptions above + keyword fallbacks. Ambiguous queries (e.g. "will I settle
abroad after marriage?") resolve to a primary domain (Marriage) with a secondary
context pull (Foreign) — CE supports multi-domain context assembly from day one.

## Known convention flags to resolve against the reference corpus
1. Father = 9th vs 10th house (school split)
2. Number/gender of children — low-confidence, consider excluding from product
3. Longevity/death predictions — excluded by policy regardless of classical basis
4. D6 varga rule is VERIFY-flagged in the engine (health domain depends on it)
5. Imprisonment/litigation outcomes — advisory tone, no deterministic verdicts
