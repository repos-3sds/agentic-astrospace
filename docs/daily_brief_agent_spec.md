# Agent-written daily brief: coverage and scheduling spec

Status: source of truth for the agent daily brief build (2026-10-16). Written from main at bf8dcfd.

## 1. How today's brief is made

Everything comes from `daily_guidance()` in `astrospace/context/daily.py`, served by `GET /api/v1/context/{kundli_id}/daily`. It is pure rules: no model call. The spoken version is assembled on the phone by `buildTodayAudioScript()` in `ui/src/app/features/mobile/today/audio-reading-script.ts`.

**Signals computed per profile, per Vedic day (sunrise to next sunrise, at the timing place):**

| Signal | Where | What it drives |
| --- | --- | --- |
| Tarabala (tara name, count of 9) | `personal_panchanga` | Day score, the tarabala do/avoid row, plain why line 1 |
| Chandrabala (house from natal Moon, chandrashtama flag) | `personal_panchanga` | Day score, Health avoid when chandrashtama, plain why line 2 |
| Ghatak alerts (matched markers) | `personal_panchanga` | Day score, Health avoid row |
| Gochara rules, supportive and challenging, with Ashtakavarga bindus | `assemble_daily_context` | Day score, domain do/avoid rows, plain why line 3, technical why |
| Dasha chain (maha / antar / pratyantar / sookshma) | `chart.dashas()` | Career do row (the lord's theme), technical why |
| Panchanga: tithi, nakshatra, yoga, karana, vara, Moon rashi, masa (amanta and purnimanta) | `daily_panchanga` | Star of the day, panchanga details, masa |
| Muhurta windows: Rahu Kalam, Yamaganda, Gulika, Abhijit | `day_payload.windows` | Timing note, verdict's practical clause |
| Favourable points: colour, number, gem, metal, direction, days, numerology | `favourable_points`, `_day_color`, `_day_number` | Lucky signature, colour and number of the day |
| KB references routed by the day's tone (health / wealth / career) | `get_knowledge_base().retrieve` | Sources behind the card |

**What the person reads and hears:**

- **Verdict:** tone (supportive / positive / mixed / caution), score, headline, a 5 to 6 sentence text that ends with the Rahu Kalam clause.
- **Reading:**
  - Summary, focus and energy.
  - Best for and avoid (up to 4 each).
  - Relationship, money and work tones.
  - Timing note (Rahu Kalam time).
  - Plain why (3 lines) and technical why (nakshatra, tithi, tarabala, chandrabala, dasha, up to 3 transit rules, Rahu Kalam).
- **Do today and avoid today:** one tarabala row plus the top 2 life-domain rows per side. The domains are Finance, Love, Health, Growth and Career.
- **Fixed facts shown as-is:** colour, number, lucky signature, lucky numbers, star of the day, panchanga details, masa and muhurta windows.
- **Listen script, in order:**
  1. Opening: "Namaste {first name}", date, city, and a lead line by tone.
  2. Overview: headline, summary and focus.
  3. Today: the first do, the first avoid and the timing note.
  4. Why: 1 to 2 plain lines. Balanced mode adds tarabala and chandrabala. Practitioner mode adds tithi, nakshatra, Moon rashi and the technical rows.
  5. Close.
- **Tone setting:** "Gentle" softens must, avoid and bad.

**The weakness Hawk is pointing at:** the inputs are personal, but the words come from fixed tables (`_DOMAIN_PHRASES`, `_CAREER_THEME`, the per-tone dicts in `_verdict` and `_reading`). So two people with the same tone hear near-identical sentences.

## 2. What the agent must cover (acceptance checklist)

The agent writes the **words**. The engine keeps the **facts**. The agent never computes or restates a time, number, colour or panchanga element on its own; it is given them and must quote them exactly.

The agent's output must still carry every one of these, grounded in that day's signals:

1. Verdict tone. Use the engine's tone and score unchanged; the agent may not upgrade or downgrade the day.
2. Headline and a short overview: summary, focus and energy.
3. Do today and avoid today, at most 4 each. Each one is tied to a named source signal: tarabala, chandrabala or chandrashtama, a ghatak marker, a named gochara rule, or the running dasha lord. Every life domain the engine flagged must appear on the right side.
4. Relationship, money and work tones.
5. The timing note, with the Rahu Kalam time quoted exactly as given. Mention Abhijit when the engine lists it.
6. Plain why: one line each for tarabala, chandrabala and the strongest transit.
7. Technical why, kept as the engine's rows. Do not have the model rewrite them; practitioners rely on them verbatim.
8. Practitioner mode: tithi, nakshatra, Moon rashi, and the dasha chain named.
9. The fixed facts (colour, number, lucky signature, panchanga details, masa, windows) pass through from the engine untouched.
10. A spoken script (see 3).

**Non-negotiables, from CLAUDE.md:**

- No death, longevity, medical, legal or financial verdicts.
- A dosha, chandrashtama or ghatak marker is a flag, never a verdict. It is never suppressed and never escalated.
- Remedies are traditional practice, never "pay to remove".
- Run the same guards Readings and Ask use on every field before saving: `prohibited_verdict()` and `dosha_overclaim_kind()` in `astrospace/agents/safety.py`. Any hit means the template brief is used for that day.

## 3. Spoken length: under 1.5 minutes at 0.9x

The listen sheet estimates duration as `words / 2.35 / speed` seconds (`listen-sheet.component.ts`). At 0.9x, 90 seconds is 2.35 × 0.9 × 90 ≈ 190 words for the whole script, greeting and close included.

- Target **150 to 180 words**, hard cap **185**. This is checked in code, not just asked of the model. If the model goes over, the first fix is to drop sentences from the end of the overview. If it is still over, use the template script.
- Natural voice is generated at 0.95x and the sheet's 0.9x maps onto it (`NATURAL_BASE_SPEED`), so the same cap holds for Chirp audio.
- Telugu: translate the capped English script. Do not have the model write a fresh long Telugu one. Spoken Telugu runs longer per word, so re-check the Telugu word count against the same budget and trim the overview if needed.

## 4. Generate on a schedule and save it: never on tap

**Hawk's requirement:** the brief is ready before the person opens the app. Tapping Listen plays immediately. Once made, it is never regenerated for that day.

**Storage:** use the existing `daily_guidance_cache` table. It is already in production (`supabase/migrations/20260725120000_create_mobile_app_schema.sql`), and `crud_mobile.get_cached_daily_guidance` / `put_cached_daily_guidance` already exist and are wired into account deletion. No migration is needed.

- Key: `kundli_id`, `local_date` (the Vedic date), `conventions_hash` and `language`.
- `conventions_hash` = hash of ayanamsha, node type, the timing place, the birth details (`kundli.updated_at`), and a `brief_engine_version` constant.
  - Editing the birth details or bumping the brief version gives a new key. That is the only way a brief is ever regenerated.
- `payload` = the agent fields, plus `source: "agent" | "template"`, `model`, token usage and `generated_at`.
- `expires_at` = the engine's `valid_until` (next sunrise).

**Scheduler:** the notification worker (`python -m astrospace.notifications.worker --once`) is not scheduled in production yet. Schedule it every 15 minutes, either as Cloud Scheduler hitting a Cloud Run Job, or a Cloud Run Job with a cron trigger.

- Add one stage, `prepare_daily_briefs`, before `schedule_morning_briefs`.
- For each profile that should have a brief, when the profile's local time is between 60 and 15 minutes before its morning push time (default 07:00):
  1. Compute `daily_guidance`.
  2. Make one Gemini call: structured output, no tools, low thinking.
  3. Run the guards and the word cap.
  4. Save the English row.
  5. If the user's language is Telugu, translate and save a `te` row.
  6. If the user has natural voice (Plus), render the Chirp audio per section into the existing GCS cache (`ASTROSPACE_TTS_BUCKET`) and record it in `audio_renders`.
- Which profiles: every user's primary profile (the same rule `_primary_kundli` uses), plus any other profile opened in the last 7 days. Not every profile in the database.
- The worker is idempotent: if a row exists for the key, it does nothing. Postgres `SKIP LOCKED` (already used for jobs) or a unique-insert race keeps two replicas from paying twice.

**Serving:**

- `GET /context/{id}/daily` returns the engine payload with the cached agent fields merged in when a row exists.
- On a cache miss it generates **once**, for example for a brand-new profile or a missed schedule. A per-key lock stops two taps from making two calls; the second request waits for, or reads, the first. The result is saved.
- Never generate on Listen. Listen reads the saved script, and Chirp audio from the bucket.
- If the agent call fails or a guard trips, save the template brief for that key with `source: "template"`. The reader always gets a brief, and a broken day does not retry on every open. One retry is allowed on the next worker pass if the failure was a provider error.

## 5. Time and cost

- **Time:** one structured call over about 3 to 4k input tokens takes a few seconds. Off the tap path, it does not affect what the user feels.
- **Cost:** about $0.01 to $0.02 per brief on gemini-3.5-flash (about $1.50 per million tokens in and $9 per million out, from third-party price trackers; confirm on Google's page). That is about $0.30 to $0.60 per profile per month.
- **Logging:** log every call's token usage as `daily_brief.cost`, the same way Ask logs `ask.cost`, so the real cost is measured after the first night rather than estimated.

## 6. Tests the build should carry

- The coverage checklist in 2: a stubbed model that omits a flagged domain or the Rahu Kalam time is rejected and falls back to the template.
- The word cap: a 300-word stub reply is trimmed or falls back, and is never saved over 185.
- The guards: a stub reply with a death or medical verdict, or an escalated dosha, falls back.
- The cache: a second request for the same key makes no model call. Changing the birth details makes a new key.
- The worker: running it twice for the same day makes one call per profile.
