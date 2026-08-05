# Mobile Screen Build Plan

Implementation tracker for the designed native app. Source of truth is the
Figma file `RRhuTcaKIhqILZW7JUKFzI` (page `0:1`); node IDs below are what
`get_design_context` takes, so a screen can be picked up without re-deriving
anything.

## How to build one

```
1. get_design_context(fileKey=RRhuTcaKIhqILZW7JUKFzI, nodeId=<node>)
2. Download any new exported assets into ui/public/mobile/
3. Build under ui/src/app/features/mobile/<screen>/ using the tokens in
   src/styles-mobile.scss and the mixins in features/mobile/mobile-tokens.scss
4. Route it under /m, verify in the browser at 375x812, screenshot
5. Re-verify natively: npm run build:native:dev, then rebuild in Xcode
```

## The two front ends do not meet

`/m/*` is guarded off the production web build by `nativeAppGuard`
(`core/native-app.guard.ts`). A production web visitor who types `/m` is sent
to `/`; native always passes, and so does any non-production build, which is
what keeps the browser verification loop alive.

This is a visibility boundary, not a security one — the mobile code still ships
in the bundle. Excluding it outright means a second build configuration, which
is a bigger change than the problem needs.

## Conventions already established

- **Tokens are global.** `src/styles-mobile.scss` defines `.as-mobile`.
  Component-scoped SCSS cannot declare them — Angular's emulated encapsulation
  rewrites the selector and every `var()` falls back silently.
- **The mobile palette owns its own light/dark pair.** Do not alias to the
  theme-reactive `--as-*` tokens; mixing produced invisible text once already.
- **Assets live in `ui/public/mobile/`**, not `src/assets`, and are referenced
  as `mobile/<name>.svg`.
- **One asset per glyph, not per size.** Figma exports a chevron at 16, 17, 18
  and 20px as four files, but they are one vector scaled — path and stroke both
  scale proportionally, and SVG scales losslessly. Diff a new export against the
  one you have before adding it, and size the leaf in CSS. Different *colour* is
  a different asset (`play.svg` vs `play-muted.svg`); different size is not.
- **Sheets use `as-sheet`** for scrim, radius, handle and safe-area padding.
- **Exported assets are used as-is.** The only exception so far is the day
  gauge, whose arc is data-driven and so is redrawn from the export's geometry.
- **Safe areas** are consumed by the shell; screens should not re-apply them.

## Running and verifying

Two backends, and the difference matters:

| Port | Config | Auth | Use for |
| --- | --- | --- | --- |
| 8000 | `astrospace` | Supabase **enabled** — needs a bearer token | the native app |
| 8010 | `astrospace-debug` | dev bypass, SQLite | browser verification |

```bash
# browser (fastest loop) — serves the built SPA
preview_start name=astrospace-debug     # -> http://localhost:8010/m/today
cd ui && npm run build:dev              # rebuild before reloading; no HMR here

# native
cd ui && npm run build:native:dev       # dev config + cap sync
cd ui/ios/App && xcodebuild -project App.xcodeproj -scheme App \
  -destination "platform=iOS Simulator,id=<udid>" \
  -configuration Debug -skipMacroValidation -derivedDataPath /tmp/astrospace-dd build
# then: control launch app_path=/tmp/astrospace-dd/Build/Products/Debug-iphonesimulator/App.app
```

The simulator needs device access granted once per session ("Let Claude use it"
on the panel), otherwise screenshots and the build tool's device lookup both
fail with a misleading "no booted simulator".

## Traps already hit — do not rediscover

- **~~Restart :8000 after any CORS change.~~ Fixed structurally — no longer a
  step.** A Capacitor WebView calls from `https://localhost`, so every API
  request is cross-origin. This used to mean a backend started before that
  origin was allowed rejected everything with a bare 400, which the app
  reported as "Supabase is not configured yet" — a CORS failure wearing a
  config failure's clothes. `main.py` now appends `_NATIVE_ORIGINS` after
  `ALLOWED_ORIGINS` unconditionally (f73e882), so a production allowlist can no
  longer drop them, and `tests/test_cors_origins.py` holds that. Restarting
  proves nothing; if you suspect CORS, ask the running server:

  ```bash
  curl -s -D- -o /dev/null -H "Origin: https://localhost" http://127.0.0.1:8000/api/v1/health | grep -i access-control-allow-origin
  ```

  An `access-control-allow-origin: https://localhost` in the response means the
  origin is live and the problem is somewhere else.
- **Verify with `npm run build:dev`, not `npm run build`.** `ng build` defaults
  to the *production* configuration, and `/m` is guarded off the production web
  build (see below) — so a production build serves the web landing page at
  `/m/today` and every screen looks deleted. Nothing is wrong; you built the
  wrong config.
- **`npx cap sync` copies whatever is already in `frontend/dist`.** Always
  build first, or the native app silently runs an old bundle.
- **The browser preview caches.** Reload after rebuilding, or you will debug a
  stale bundle.
- **The web app's global CSS still matches mobile elements.** Angular's view
  encapsulation scopes *your* rules; it does not stop a global rule in
  `styles.scss` from matching your markup. `class="hero"` on Ask picked up the
  web app's `@media (max-width: 599px)` glass card and rendered the heading on a
  dark slab. Before naming a class, check it:

  ```bash
  grep -n '\.your-class\b' ui/src/styles.scss
  ```

- **A screen routed outside the shell paints nothing.** The shell set the
  background on its own `:host`, so every screen inside it was fine — the first
  screen routed outside it (onboarding) inherited the *web app's* theme-reactive
  background and rendered `--m-text`, a near-black, on the dark theme. The
  headline was invisible. `.as-mobile` now sets `background`/`color` itself, so
  carrying the class is enough; keep it that way.
- **Everything compiles.** All four bugs found so far — silent token fallback,
  invisible text, unconsumed safe areas, and the global-class collision above —
  passed the build cleanly and were only caught by screenshots. Verify visually,
  every screen.

## Before a device build

`nativeApiOrigin` is now set in both environments, so nothing is outstanding
for a *simulator* build, and nothing is outstanding for production either —
**this was re-checked live on 2026-07-28 and is resolved.** The image running
at the deployed URL now accepts the Capacitor origin:

```
OPTIONS https://agentic-astrospace-cwuqybpnzq-el.a.run.app/api/v1/auth/config
Origin: https://localhost   ->   HTTP 200, access-control-allow-origin: https://localhost
```

A prior note here said the deployed service was still running an image built
before `https://localhost` was allowed and needed a redeploy — that image has
since rolled forward. No redeploy is needed for this specifically. If a device
build ever sees the CORS failure again, it means a *new* deploy regressed —
check the origin list with the same `curl -X OPTIONS` probe before assuming
the fix wore off.

Do *not* work around a CORS failure with `--set-env-vars ALLOWED_ORIGINS=...`.
That was the original trap: `ALLOWED_ORIGINS` replaces the dev defaults, so
while the native origins lived alongside them, pointing it at a production
domain silently dropped native support. The native origins are no longer part
of the configurable set — `main.py` always appends them, whatever
`ALLOWED_ORIGINS` says — so a routine deploy can't reintroduce this specific
failure mode. `tests/test_cors_origins.py` pins that down.

## Store submission

**Privacy manifest** — `ui/ios/App/App/PrivacyInfo.xcprivacy`, wired into the
Xcode project and verified present in a Release build (not just on disk).

`NSPrivacyAccessedAPITypes` is **empty on purpose**. A security audit predicted
a UserDefaults/CA92.1 declaration via Capacitor; grep found `UserDefaults` in
neither Capacitor's Swift sources nor this app's native code, because the
config loads only `AppPlugin` and `CAPBrowserPlugin`. Session state lives in
WebView localStorage, which is not a required-reason API. **Adding a plugin —
`@capacitor/preferences` most likely — means revisiting this file.**

**Versions** now have one source. `ui/package.json` holds the marketing version;
the build number is `git rev-list --count HEAD`, because Play rejects a
`versionCode` that does not increase and a number someone must remember to bump
is one that eventually is not bumped.

```bash
npm run version:sync     # write it into iOS + Android
npm run version:check    # fail if drifted (this is the CI form)
```

`build:native` and `build:native:dev` run the sync first, so a bundle cannot be
produced with a stale version. FastAPI's `version="2.0.0"` is deliberately left
alone: that is the *API* version, and `/api/v1` routes served by a 2.0.0
application is coherent rather than contradictory.

## Telugu is disabled — what shipping it actually needs

The language controls show Telugu and refuse it. Before that, the toggle was
live and changed **nothing**: there is no UI translation, and `language` is
stored on the message row and used to filter the `remedies` table but is never
passed to the agent, so answers came back in English either way. A control that
silently does nothing is worse than one that says it is not ready — especially
on the onboarding screen that asks for trust.

Disabled in four places: `onboarding/language.component`,
`settings/language-audio.component`, `today/listen-sheet.component` (audio), and
the Welcome promise, which used to read "English & Telugu".

Shipping it for real is a milestone, not a fix:

1. **UI localisation** — ~70 mobile components, none of which use `$localize`.
   `angular.json` has the `extract-i18n` builder from the default scaffold; no
   locale files exist.
2. **Pass `language` to generation** — it currently stops at the database.
3. **Telugu TTS** for Listen, or the audio toggle is decorative again.
4. **Extend the refer-out boundary.** This is the one with teeth. Both the
   input gate and the output net are English-only, so a Telugu speaker asking
   about death would clear the input rules, and a Telugu answer would clear the
   output net — **both layers blind at once**, for exactly the users who were
   promised the boundary in their own language. Regex cannot fix this; it needs
   model-based intent classification, which is language-agnostic by
   construction. `BaseAstroAgent` already holds an Anthropic client.

Do these together. Shipping (1) without (4) is the dangerous ordering.

## Needs a fluent Telugu speaker (when Telugu ships)

The refer-out boundary (`astrospace/api/ask_routes.py`) now matches on subject
plus verdict-frame rather than whole English phrasings, which took the probe
set from 7/31 gated to 26/26. It includes the literal Devanagari and Telugu
words for death, illness and disease — but **literal words are not coverage**.

A fluent speaker needs to review `_REFER_OUT_SUBJECTS` and answer:

- Which everyday Telugu phrasings ask about death or illness *without* using
  these words? Euphemism is exactly how this kind of rule gets walked around,
  and it is culturally specific.
- Do any of the added terms appear innocuously in ordinary questions, so that
  the gate would refuse someone unfairly?

Until that review happens, treat non-English coverage as partial. The
output-side net (`_prohibited_verdict`) is the backstop, and it is
English-only too — a Telugu-language verdict would pass it. That is the
sharpest remaining edge of this boundary.

`tests/test_refer_out_boundary.py` holds both directions: prohibited questions
gated, ordinary ones answerable. Add cases there rather than loosening rules.

## Verify when credentials are available

Work that was **mitigated, not closed**, because it needed something this
environment didn't have (Supabase project credentials, a way to trigger a
real email, or a deployed edge to probe). Each entry names the exact check
that closes it.

### Native auth callback: does the fragment path ever actually fire?

`ui/src/app/core/auth.service.ts`'s `handleNativeAuthCallback` has two
branches: a `?code=` exchange (PKCE-protected — safe on its own) and an
`#access_token=`/`#refresh_token=` fragment fallback (not safe on its own,
now gated behind a one-time state nonce — see the 2026-07-28 commit
"gate the native auth callback's fragment-token branch on state").

That gate is a mitigation, not proof the fragment path is dead. It was built
on two claims, and only one is verified:

- **Verified, from URL syntax alone, not from asking Supabase anything**: a
  `#fragment` never alters the `?query` string it follows. So whichever shape
  Supabase actually returns, a `state` param placed in the `redirectTo` query
  string survives.
- **Not verified**: whether *this Supabase project*, for the magic-link and
  password-reset flows specifically, ever returns the fragment shape at all
  (`flowType: 'pkce'` should make every flow return `?code=`, project-wide
  settings and email template can still affect this) — or, separately,
  whether the `?code=` redirect reliably preserves a pre-existing query
  string the way the implicit fragment shape unambiguously does.

**The check, exactly**: with Supabase credentials in hand —

1. Trigger a real password reset (`AuthService.resetPassword`) or magic link
   (`signInWithMagicLink`) from a native build (simulator is fine).
2. Tap the email link, let it redirect into the app, and capture the full
   URL `handleNativeAuthCallback` receives — log it once, temporarily, right
   at the top of that method.
3. Check: does it carry `?code=...`, or `#access_token=...&refresh_token=...`?
4. Repeat for `signInWithGoogle` (OAuth) as a control — this one is expected
   to always be `?code=`.

**If every flow always returns `?code=`**: the fragment branch in
`handleNativeAuthCallback`, `issueNativeAuthState`, `consumeNativeAuthState`,
`NATIVE_AUTH_STATE_KEY`, and the `state` query param appended in
`authRedirect` all become dead code for a vulnerability that can't occur —
delete them, and delete the fragment-path tests in `auth.service.spec.ts`
alongside them. Don't leave the nonce machinery in "just in case"; unused
security code is a maintenance liability, and the code-branch tests already
cover what's live.

**If the fragment shape does occur for any flow**: the gate stays, and this
section can be deleted — the assumption it now conditionally protects is
confirmed, not held on faith.

## Figma access

The working connector is the UUID-named MCP server, not `plugin:figma:figma`.
`get_design_context` requires the design-to-code skill to be loaded first:

```
get_figma_skill(uri="skill://figma/figma-design-to-code/SKILL.md")
```

## Screens

| Node | Screen | Status |
| --- | --- | --- |
| `4:2` | 1 · Landing | ✅ done — `/m/start` |
| `5:2` | 2 · Login / Register | ✅ done — `/m/auth` |
| `6:2` | 3 · Welcome | ✅ done |
| `7:2` | 4 · Info Carousel · Disclaimers | ✅ done |
| `8:2` | 5 · Persona Type | ✅ done |
| `11:2` | 6 · Birth Details | ✅ done |
| `13:2` | 7 · Today | ✅ done |
| `20:2` | 7b · Today (full scroll) | ✅ done — same component as `13:2`, scrolled |
| `21:22` | 7c · Day-quality detail | ✅ done |
| `22:23` | 7d · Why this reading | ✅ done |
| `23:25` | 7e · Listen (audio) | ✅ done — sheet over Today |
| `25:25` | 8 · Ask — Home | ✅ done |
| `25:123` | 9 · Ask — Voice listening | ✅ done — overlay from Ask's mic |
| `26:54` | 10 · Ask — Answer view | ✅ done |
| `27:83` | 11 · Ask — Refer-out (safety) | ✅ done — `?domain=health\|legal\|money\|death` |
| `29:55` | 12 · Remedies — For You | ✅ done — `/m/remedies` |
| `29:109` | 13 · Remedy detail — Mantra tracker | ✅ done — `/m/remedies/mantra` |
| `30:56` | 14 · Muhurta — Choose a goal | ✅ done — `/m/muhurta` |
| `31:57` | 15 · Muhurta — Results | ✅ done — `/m/muhurta/results` |
| `35:57` | 16 · Chart Hub (You) | ✅ done — `/m/chart` |
| `36:86` | 17 · Chart — Full render | ✅ done — `/m/chart/full`, Eastern only |
| `36:201` | 18 · Planet detail sheet | ✅ done |
| `36:247` | 19 · Provenance sheet | ✅ done |
| `39:87` | 20 · Divisional (Varga) Charts | ✅ done — `/m/chart/vargas` |
| `40:87` | 21 · Life Periods (Dashas) | ✅ done — `/m/chart/periods` |
| `41:87` | 22 · Yogas & Doshas | ✅ done — `/m/chart/yogas` |
| `41:149` | 23 · Strength & Advanced | ✅ done — `/m/chart/strength` |
| `41:210` | 24 · Learning sheet — Gajakesari Yoga | ✅ done |
| `56:88` | 17b · Chart — Full render (South) | ✅ done — style toggle in `/m/chart/full` |
| `57:88` | 17c · Chart — Full render (North) | ✅ done — style toggle in `/m/chart/full` |
| `59:88` | 21b · Life Periods — Maha level | ✅ done — `/m/chart/periods` Maha tab |
| `59:258` | 21c · Life Periods — Pratyantar level | ✅ done — `/m/chart/periods` Pratyantar tab |
| `59:427` | 21d · Life Periods — Yogini system | ✅ done — `/m/chart/periods` Yogini tab |
| `60:88` | 23b · Strength & Advanced — Ashtakavarga | ✅ done — Ashtakavarga tab |
| `60:257` | 23c · Strength & Advanced — Jaimini | ✅ done — Jaimini tab |
| `61:88` | 20b · Divisional charts — D1 | ✅ done — D1 selector in `/m/chart/vargas` |
| `61:195` | 20c · Divisional charts — D10 | ✅ done — D10 selector in `/m/chart/vargas` |
| `62:88` | 2b · Register | ✅ done — `/m/auth?mode=register` |
| `62:140` | 12b · Manglik cancellation detail | ✅ done — shared from Chart and Remedies |
| `66:89` | 25 · Settings — Home | ✅ done — `/m/settings`, the More tab |
| `67:89` | 25b · Settings — Mode & Tone | ✅ done |
| `67:147` | 25c · Settings — Language & Audio | ✅ done |
| `67:173` | 25d · Settings — Notifications | ✅ done |
| `69:89` | 25e · Settings — Location | ✅ done |
| `69:117` | 25f · Settings — Conventions | ✅ done |
| `69:180` | 25g · Settings — Account & Privacy | ✅ done |
| `79:89` | 26 · Profile switcher sheet | ✅ done — shared from Today and Settings |
| `82:96` | 2c · Choose Your Language | ✅ done — `/m/language` |
| `91:89` | 27 · Gochara (plain transits) | ✅ done — `/m/transits` |
| `92:89` | 27b · Full Transits | ✅ done — `/m/transits/full` |
| `93:89` | 28 · Calendar | ✅ done — `/m/calendar` |
| `94:118` | 29 · Festival detail sheet | ✅ done — sheet from Calendar |
| `97:119` | 30 · Compatibility Hub | ✅ done — `/m/compat` |
| `97:144` | 30b · Add Prospect | ✅ done — `/m/compat/add` |
| `98:119` | 30c · Gun Milan Results | ✅ done — `/m/compat/results` |
| `108:92` | 7-dark · Today (Dark mode) | ✅ done — shared dark mobile token mode |
| `108:186` | 8-dark · Ask Home (Dark mode) | ✅ done — shared dark mobile token mode |
| `108:246` | 16-dark · Chart Hub (Dark mode) | ✅ done — shared dark mobile token mode |
| `108:417` | States · Ask — Loading (computing answer) | ✅ done — `/m/ask/loading`, wired during generation |
| `110:121` | States · Compatibility — Empty (no checks yet) | ✅ done — default state at `/m/compat` |
| `110:153` | States · Generic — Something went wrong | ✅ done — reusable `as-generic-error` |
| `113:122` | 31 · Readings & Accuracy | ✅ done — `/m/readings` |
| `114:124` | 31b · Prediction Claims (accuracy) | ✅ done — `/m/readings/accuracy` |
| `115:124` | 32 · Notes | ✅ done — `/m/notes` |
| `116:124` | 28b · Calendar — Day detail (timing feed) | ✅ done — `/m/calendar/day` |
| `117:124` | 33 · Practitioner Reference | ✅ done — `/m/chart/reference` |
| `117:175` | 33b · Avkahada & Ghatak | ✅ done — `/m/chart/reference/avkahada` |
| `118:124` | 33c · Graha positions & conditions | ✅ done — `/m/chart/reference/grahas` |
| `118:239` | 33d · Ashtakavarga tables | ✅ done — `/m/chart/reference/ashtakavarga` |
| `118:383` | 33e · Favourable points | ✅ done — `/m/chart/reference/favourable` |

## New frames added 2026-07-27

These frames were discovered in the updated Figma page after the original
70-screen inventory. Full design context has been fetched for every node.

| Node | Screen | Status | Workflow dependency |
| --- | --- | --- | --- |
| `206:160` | 2d · Forgot Password | ✅ done — `/m/forgot-password` | US-N5 · request, non-enumerating confirmation, and return-to-sign-in journey |
| `206:190` | States · Chart Computing | ✅ done — shown during birth-detail recalculation | US-N4 |
| `206:223` | 10b · Ask — History | ✅ done — `/m/ask/history` | US-N2 · list, reopen, continue, and archive persisted Ask threads |
| `206:302` | 34 · Subscription | ✅ screen — `/m/subscription`; purchasing intentionally disabled | StoreKit/Play entitlement contract still requires product approval |
| `206:354` | 35 · Notification Center | ✅ done — `/m/notifications` | Real alert persistence, mark-read, and safe mobile deep links |
| `206:493` | 6b · Edit Birth Details | ✅ done — `/m/settings/birth-details` | US-N3 · edit active kundli, recalculate chart, and invalidate derived caches |
| `206:550` | 27c · Transit Detail | ✅ done — shared sheet from Gochara and Full Transits | US-N4 |
| `206:591` | 36 · Search | ✅ done — `/m/search` | Cross-module client index with working result deep links and recent searches |
| `206:641` | 25h · Account Deletion | ✅ done — `/m/settings/account/delete` | Backend-confirmed user-scoped cascade with regression tests |

## New frames added 2026-07-29

A second, later batch (node IDs `103:xxx`–`269:xxx`) that neither the original
inventory nor the 2026-07-27 batch above ever caught — found via a full
top-level frame sweep, not the keyword search the first pass used. Per-persona
screen variants, native OS surfaces, and edge-case states. Acceptance criteria
for everything not yet done are in
[Persona & Platform Parity](#persona--platform-parity--implementation-checklist-2026-07-29).

| Node | Screen | Status |
| --- | --- | --- |
| `212:161` | 7G · Today (Guided) | ⚠️ partial — same component as Balanced, mode-specific layout not built |
| `212:324` | 7B · Today (Balanced) | ✅ done — this is the shipped baseline `today.component` |
| `212:751` | 7P · Today (Practitioner) | ✅ done 2026-07-29 — Active Period Stack, Panchanga Details, Critical Gochara Transits, Significant Horary Timings, all live-computed |
| `212:416` / `458` / `512` | 6c/6d/6e · Aha — Guided/Balanced/Practitioner | ✅ done 2026-08-04 — `first-insight.component` now computes from the just-cast kundli (`VedicService.all`) instead of hardcoded literals, one branch per persona |
| `212:971` / `1019` / `1077` | 10G/10B/10P · Ask Answer | ❌ not built — one answer template serves all modes |
| `214:155` | 16P · Yantra (Practitioner) | ❌ not built |
| `215:156` | 12G · What to do (Guided) | ⚠️ partial — tab label routes to the generic Remedies screen, not a dedicated Guided layout |
| `215:241` | Profiles · Today Across Profiles | ❌ not built — no multi-profile dashboard exists |
| `215:373` | 16G · Your Story (Guided) | ❌ not built — Guided mode reuses the Balanced/Practitioner Chart Hub |
| `215:620` / `690` | 28G/28P · Calendar Day | ❌ not built — one Calendar Day layout serves all modes |
| `215:805` | 30d · Full Compatibility Detail | ❌ not built — shipped Gun Milan Results is the summary card only |
| `215:1216` | 16P · Charts (Practitioner) | ❌ not built |
| `216:160` / `262` | 21e/21f · Life Periods — Sookshma/Prana | ❌ not built — grepped `life-periods.component.*`, no match |
| `216:415` | 37 · Manage Profiles | ✅ close — live-verified on device, matches Figma closely |
| `216:483` | 37b · Add Profile | ✅ done — `/m/settings/profiles/new` |
| `216:543` | screen-3-edit-profile | ⚠️ partial — edit form exists; missing Gender field and the Danger Zone's Archive option |
| `216:615` | screen-4-delete-confirmation | ⚠️ partial — has type-to-confirm, but types the literal word "DELETE" not the profile's name |
| `216:773` | States · Offline / Stale Data | ❌ not built — grepped `core/` and `features/mobile/` for "offline"/"stale", no match |
| `216:838` | States · Partial Calculation | ❌ not built — pairs with unknown-birth-time below |
| `216:904` | screen-3-unknown (unknown birth time) | ❌ not built — grepped both birth-details components, no "unknown" field anywhere |
| `216:964` | screen-4-denied (notification permission denied) | ❌ not built |
| `103:92`–`107:101` | M10 · Home/Lock Screen Widget, Live Activity, Watch Complication, Push Notification, Share Story Card | ❌ not built — see Platform (M10) below; most need native extension targets, not just Angular work |
| `269:158` | enhanced-stat-cells-concept | Not a spec'd screen — reads as a live design exploration (was the current selection in the Figma desktop app when checked) |

### Recommended implementation order

1. **Ask History (`206:223`)** — it completes the active US-N2 thread journey
   already supported by `/api/v1/ask/threads`.
2. **Forgot Password (`206:160`)** and **Edit Birth Details (`206:493`)** —
   close existing account/profile lifecycle gaps with APIs already present.
3. **Chart Computing (`206:190`)** and **Transit Detail (`206:550`)** — state
   and drill-down surfaces needed when US-N4 replaces fixtures with live data.
4. **Account Deletion (`206:641`)** — build only with a confirmation-bound
   backend cascade and tests; the screen must never delete locally by itself.
5. **Notification Center (`206:354`)** and **Search (`206:591`)** — require
   shared backend contracts and reliable deep links before UI implementation.
6. **Subscription (`206:302`)** — defer until entitlement rules, App Store /
   Play billing, restore-purchase behavior, pricing ownership, and premium
   feature boundaries are approved.

## Not yet wired

Ask's composer routes every question to the answer view (26:54), including
ones that must refer out. Choosing between 26:54 and 27:83 is the answer
pipeline's call — classifying intent in the client would put the safety
boundary somewhere that can be bypassed. Both screens exist and are routed;
the decision lands with `/api/v1/ask`.

### Next implementation order

The next milestone is workflow wiring, not another batch of isolated screens.
Use `docs/full_astro_software_checklist.md` US-N1 through US-N6 as the ordered
execution backlog:

1. Restore a real active profile and load Today from the daily-context API.
2. Complete the backend-owned Ask safety and history journey.
3. Build and wire profile switching/management.
4. Replace fixture data module-by-module, including loading/empty/error states.
5. Finish account lifecycle against real Supabase.
6. Complete remaining Figma variants and native release verification.

For each story, verify the complete journey at 375 × 812 and commit the story
as one coherent slice. Do not mark a screen's workflow complete merely because
its static Figma implementation renders.

## Status

All 79 inventoried Figma frames are implemented and routed. Subscription is
present as a faithful, explicitly disabled screen because pricing,
entitlements, restore-purchase behavior, and StoreKit/Play ownership have not
yet been approved; it must not simulate a purchase.

**This "79 frames" count is now known to be incomplete.** A 2026-07-29 sweep of
the same Figma page found a second batch of frames (node IDs `103:xxx`
through `269:xxx`) covering per-persona screen variants, native OS surfaces,
and edge-case/resilience states that were never added to this inventory —
see [Persona & Platform Parity](#persona--platform-parity--implementation-checklist-2026-07-29)
below. Remaining work is that parity buildout plus workflow hardening and
native release verification, not just the latter.

## Persona & Platform Parity — Implementation Checklist (2026-07-29)

**Status note, 2026-08-04:** this section is now historical for the
persona/platform frame sweep. For the current bug triage, verification status,
and acceptance criteria, use
[Mobile Stabilization Checklist — 2026-08-04](#mobile-stabilization-checklist--2026-08-04)
below. If a row here conflicts with that dated checklist, the 2026-08-04
stabilization checklist wins until the final regression audit reconciles both.

Source: [docs/mobile_figma_web_persona_gap_analysis.md](mobile_figma_web_persona_gap_analysis.md)
(2026-07-27 audit) plus the frame sweep above. That audit is the detailed
rationale for *why* each gap matters; this checklist is what closes it. Check
an item here — don't re-derive it from the audit — and update the audit's own
status note if a whole section it describes is now closed.

Items already shipped this session are marked done with their acceptance
criteria for traceability; everything else is open with the criteria that
close it.

### Done (2026-07-29)

- [x] **Persona nav bar icons match Figma.** Guided "What to do" uses
      check-square, Balanced "Chart" uses git-branch, Practitioner
      Chart/Periods/Transits/More use star/clock/map-pin/settings-gear.
      AC met: verified live in-browser for all three modes; icons render
      pixel-identical to their Figma source nodes (`212:214`, `212:391`,
      `212:898`).
- [x] **Practitioner Today board** (`212:751`). AC met: Active Period Stack
      shows all 4 dasha levels (maha/antar/pratyantar/sookshma) with live
      lord names; Panchanga Details shows tithi/nakshatra/yoga/karana/vara
      from real engine output; Critical Gochara Transits shows each active
      rule's AV bindus (or "AV —" for non-bindu planets); Significant Horary
      Timings lists all 4 muhurta windows with real times. Backed by
      `astrospace/context/daily.py`'s `panchanga_details`/`muhurta_windows`/
      `av_bindus` fields (743 backend tests + 4 frontend unit tests pass).
- [x] **Guided Today variant** (`212:161`). AC met: eyebrow reads "YOUR VIBE
      TODAY", no numeric gauge (prose-only verdict), DO/AVOID icons are
      trending-up/alert-triangle (downloaded from Figma, not the
      checkmark-circle/x-circle used elsewhere), Listen button reads
      "Listen to your day (2 min brief)". Verified live in-browser.
- [x] **Life Periods Sookshma/Prana** (`21e`/`21f`, nodes `216:160`/`262`).
      AC met: two more tabs alongside Maha/Antar/Pratyantar, each showing
      the active chain's breadcrumb and a real timeline list, sourced from
      `chart.dashas()`'s existing `sookshmadasha`/`pranadashas` output — both
      levels confirmed present in `dashas.py` (not just `sookshmadasha` as
      originally assumed here). Found and fixed a real bug along the way:
      the tab bar's CSS was built for exactly 3 equal-flex tabs, and 5 tabs
      overlapped without a gap ("PratyantarSookshma" rendered as one run of
      text) — changed `.levels` to scroll horizontally instead of forcing
      an ever-shrinking flex-basis.
- [x] **Full Compatibility Detail** (`30d`, node `215:805`). AC met: new
      `/m/compat/results/detail` screen shows all 8 Kootas with per-koota
      status badges (✓/CAUTION/PARTIAL), a Special Cancellations section
      (surfaces any row whose engine-authored note says "cancelled" — no
      new detection), and a Safety Checks section. The Safety Checks section
      needed a real backend addition: `compatibility.py` had no Manglik or
      Gandanta cross-check between the two charts at all, so added
      `_safety_checks()` reusing the existing `manglik_dosha()`/
      `gandanta_dosha()` functions (not a second implementation) and wired
      it into `gun_milan()`'s response. "Compare D1/D9" stays disabled (real
      feature, not built, not faked); "Gen AI Narrative" links to Ask with
      the question pre-filled, reusing Ask's existing generation rather than
      a second AI path. Required updating two test doshas/compat stub
      fixtures (`tests/test_doshas_compat_v2.py`, `tests/test_vedic.py`)
      that didn't model `positions`/`lagna_lon` — all 743 backend tests
      pass, including the newly-fixed ones.
- [x] **Delete confirmation types the profile's name** (`screen-4-delete-
      confirmation`, node `216:615`). AC met: now requires the profile's
      actual name instead of the literal word "DELETE".

Also observed already done in the working tree by the time this pass ran
(not built in this session, noted here so the tracker stays accurate):
Guided mode's "What to do"/"Chart" merged into a persona-appropriate
`Explore`/`Your Story` flow (`ui/src/app/features/mobile/explore/`,
routes `/m/explore`, `/m/explore/story`, `/m/explore/what-to-do`,
`/m/explore/life-chapters`), and Practitioner's Chart tab relabeled
"Yantra" per node `214:155` with its own icon set
(`figma-yantra-nav-*.svg`). Both compiled and passed the full test suite
alongside this session's changes.

### Done (2026-08-05) — new-user journey polish

Three more fixes beyond the Aha screens above, none of them a missed Figma
node — logged here so the "done" list stays a complete record of what
changed, not just what Figma asked for:

- **`m/language` now persists.** The screen looked functional but never
  wrote its selection anywhere — `PreferencesService.language` is now set
  on entry. Telugu stays visibly disabled; see "Telugu is disabled" above.
- **`m/welcome`'s "carousel" is now an actual carousel.** It was 3 static
  stacked cards with no swipe interaction. Rebuilt as a real horizontal
  scroll-snap carousel (4 slides, dot indicators, tap-to-jump) with fresh
  copy grounded in what the app actually does — no Figma pull for this one
  (connector unauthenticated this session; node `7:2` has no slide-level
  content spec in this doc either, see "New frames added 2026-07-29" table
  above).
- **New `/m/customize` step** between Persona and Birth Details (not a
  Figma-tracked node — an intentional post-launch addition). Chart style
  and festival-region were real, working `PreferencesService` fields with
  no onboarding UI at all; a new user only found them by accident later in
  Settings. One combined screen, not two, to avoid adding two full steps to
  signup. Persona is now "STEP 1 OF 3", this is "STEP 2 OF 3", Birth
  Details is "STEP 3 OF 3" (was "STEP 2 OF 2").

### P0 — Core persona variants

- [x] **Onboarding "Aha" result screens** (`6c`/`6d`/`6e`, nodes `212:416`/
      `458`/`512`). AC met 2026-08-05: `first-insight.component.ts` now
      injects `VedicService`/`KundliStore` and computes from the kundli
      `birth-details` just created (via `buildChartAdapter`, the same
      adapter Chart Hub uses) instead of a hardcoded literal shown to every
      user. Guided shows the real signature line, the highest-Shadbala
      planet as "one strength", a hedged one-line action tied to it, and a
      real "Listen" deep link (`/m/today?listen=1`, now actually wired —
      `today.component.ts` previously ignored that query param entirely).
      Balanced shows the real signature plus real Sun/Moon/Ascendant, with
      "Preview today"/"Preview chart" links. Practitioner renders the real
      D1 chart via the shared `KundliChartComponent`, real birth constants
      (ayanamsha/node/house-system/timezone), and the real current dasha
      chain, reusing Chart Hub's `.period-chain`/`.period-pill` pattern.
      All three keep "Continue to Today" reachable even if the chart fetch
      fails — the Aha moment is a bonus, never a gate.
- [ ] **Ask Answer persona variants** (`10G`/`10B`/`10P`, nodes `212:971`/
      `1019`/`1077`). AC: Guided shows short verdict/action/caution only;
      Balanced is today's shipped answer view; Practitioner adds question
      scope (profile/date range/location/domain/chart), natal-promise vs.
      active-dasha vs. gochara sections, and visible source/provenance
      links — all three read the same underlying `/api/v1/ask` response,
      no separate calculation path.
- [ ] **Chart Hub persona variants** (`16G`/`16P`, nodes `215:373`/`1216`).
      AC: Guided is relabeled "Your Story", leads with strengths/life areas,
      and moves Vargas/Shadbala/AV/Jaimini under an "Advanced" disclosure;
      Practitioner is a workbench landing (D1/D9 + current period + gochara
      + graha table + quick style/ayanamsha controls); Balanced keeps the
      shipped Chart Hub unchanged.
- [ ] **Calendar Day persona variants** (`28G`/`28P`, nodes `215:620`/`690`).
      AC: Guided shows observances/next-window/reminders in plain good-avoid
      language only; Practitioner adds the full window list (Hora,
      Durmuhurta, Gulika, Disha Shool, Panchaka, Bhadra) with provenance and
      timezone; both read the same day-detail endpoint as the shipped
      Balanced view.

### P0 — Multi-profile & birth-data states

- [ ] **"Today Across Profiles" dashboard** (`215:241`). AC: new screen
      listing every profile with a one-line daily status and current
      Mahādasha per profile, plus a single cross-profile "Today's Top
      Alert" callout surfacing the most urgent item (e.g. an active
      Chandrashtama); reachable from the profile switcher, not just a
      renamed switcher sheet.
- [ ] **Unknown/approximate birth time** (`screen-3-unknown`, node
      `216:904`, pairs with `States · Partial Calculation`, node `216:838`).
      AC: both `onboarding/birth-details.component` and
      `settings/edit-birth-details.component` gain an "Unknown" toggle for
      time of birth; choosing it shows the "works normally vs. limited
      features" explainer and a fallback-mode choice (sunrise default /
      noon-Madhya); any chart computed from a fallback time is marked
      "APPROXIMATE" wherever house/dasha-dependent data is shown, with the
      ±1 house / ±6 month uncertainty note from the Figma reference.
- [ ] **Profile Archive, distinct from Delete** (`screen-3-edit-profile`,
      node `216:543`). AC: edit-profile screen gains a "Danger Zone" with
      two distinct actions — Archive (hides from Today/notifications,
      preserves all data, reversible) and Delete (current behavior);
      Archive must not touch `crud.py`'s delete cascade.

### P0 — Resilience states

- [ ] **Offline / stale-data banner** (node `216:773`). AC: when a network
      request fails and a previously-cached response exists, show a banner
      ("You're offline. Showing last updated results from Xh ago.") with a
      Retry action, rather than either a blank error state or silently
      stale content; applies at minimum to Today and Calendar Day.
- [ ] **Notification permission denied screen** (`screen-4-denied`, node
      `216:964`). AC: shown when the OS reports notifications denied;
      explains what's missed (morning guidance, transit alerts, timing
      windows) with "Open Settings" and "Remind me later" actions; ties
      into the still-outstanding push notification registration work
      below.

### P1 — Trust and completeness (see the 2026-07-27 audit §7 for full detail)

- [ ] Appearance & Accessibility settings screen (theme, text size,
      contrast, motion, screen reader).
- [ ] Search entity filters, empty state, and result-destination rules.
- [ ] Reading/history empty, loading, retry, and version-comparison states.
- [ ] Remedy alternatives (cost/mobility/dietary/religious substitutions)
      and evidence-strength display.
- [ ] Muhurta filtering, saved-window management, and timezone clarity.
- [ ] Regional festival rules and location-sensitive observance behavior.

### P2 — Platform (M10 native surfaces)

None of these are Angular/Capacitor work — each needs its own native
extension target, which is a separate build system and, for the watch app,
a separate App Store product.

- [ ] **Push notification registration** (node `106:109`). AC:
      `@capacitor/push-notifications` wired, APNs cert + FCM key
      configured, device token persisted server-side, morning-brief payload
      sent on schedule. Tracked as not-done since `docs/native_builds.md`'s
      original M11-US04.
- [ ] **Share Story Card** (node `107:101`). AC: `@capacitor/share` plus a
      canvas-rendered 9:16 image of the day's headline, shareable to
      WhatsApp Status / Instagram Stories from the Today screen.
- [ ] **Home Screen Widget** (node `103:92`). AC: iOS WidgetKit extension +
      Android App Widget provider, both reading the same daily-guidance
      data, medium-size layout matching the Figma mock.
- [ ] **Lock Screen Widget** (node `104:92`). AC: iOS Lock Screen widget
      (circular) via the same WidgetKit extension.
- [ ] **Live Activity / Dynamic Island** (node `106:92`). AC: ActivityKit
      integration showing the active/next muhurta window with a live
      countdown, started when a window begins and ended when it lapses.
- [ ] **Watch Complication** (node `106:102`). AC: a watchOS app target
      exists and ships a complication showing the day's score and label.

### Recommended sequence

Phased by risk and how much the data already exists (checked against the
engine before ordering, not guessed):

1. **Cheap wins — data already computed, frontend-only. Done 2026-07-29.**
   Guided Today variant; Life Periods Sookshma/Prana; Full Compatibility
   Detail (needed one real backend addition — Manglik/Gandanta safety
   checks didn't exist yet, see the Done list above); delete-confirmation
   name-match fix.
2. **New screens, moderate wiring.** Ask Answer / Chart Hub / Calendar Day
   persona variants; onboarding Aha result screens (net-new route).
3. **Backend/engine work.** Unknown/approximate birth time (touches chart
   computation itself, not just a form field — treat with the same care as
   any `astrospace/core/vedic/` change); Partial Calculation state (depends
   on this); Today Across Profiles (new aggregation endpoint); Profile
   Archive (schema change, separate from the delete cascade).
4. **Resilience.** Offline/stale banner; notification-permission-denied
   screen.
5. **P1 items**, deferred until 1–4 close.
6. **P2 native platform (M10).** Its own track — WidgetKit extension,
   ActivityKit, a watchOS target, APNs/FCM setup. Don't start without an
   explicit go-ahead; the watch app alone is a separate App Store product.

## Mobile Stabilization Checklist — 2026-08-04

This is the active tracker for the user-reported mobile quality bug list from
2026-08-04. Use this section before changing any older 2026-07-29 status row.
Statuses are deliberately stricter than "code exists":

- `[x]` means implemented and verified enough to treat as closed.
- `[~]` means implemented or improved, but still needs native verification,
  deeper architecture, or content/data hardening.
- `[ ]` means open.

Do not mark an item `[x]` unless it is verified in a 375 x 812 browser/mobile
preview and, where native behavior is involved, on the connected Android phone.
Final proof belongs in `docs/mobile_ui_regression_audit.md`; this checklist is
the live remediation tracker.

### Verified or sufficiently closed

- [x] **Settings menu icon consistency** — P2.
  Routes: `/m/settings`.
  AC: every Settings row uses a semantic icon; icons share one visual family;
  light/dark colors remain visible; no duplicate gear/clock misuse remains.
  Evidence: source mapping updated in `SettingsHomeComponent`; semantic
  `set-*` assets added for appearance, tone, interaction, festival, inbox and
  Plus.

- [x] **Reflect with SIDDHA fallback** — P3.
  Route: `/m/today`.
  AC: the section never renders empty; at least one fallback prompt routes to
  Ask; the section does not look like an unfinished block when daily prompts
  are unavailable.
  Evidence: Today renders fallback suggestion when `askSuggestions` is empty.

- [x] **Ask construction response while AI is disabled** — P2.
  Routes: `/m/ask`, `/m/ask/loading`, `/m/ask/answer`.
  AC: typed questions and suggested questions land on an explicit
  "SIDDHA Agents are under construction" response; the app does not imply a
  fake live AI answer.
  Evidence: Ask loading routes to answer preview instead of calling the live
  Ask endpoint for this disabled module.

- [x] **Dasha tab visibility** — P2.
  Route: `/m/chart/periods`.
  AC: Maha, Antar, Pratyantar, Sookshma and Prana are visible/reachable on
  mobile without text collision.
  Evidence: five-level life-period tabs are present and horizontally scroll.

- [x] **Yoga detail hardcoded Gajakesari bug** — P2.
  Route: `/m/chart/yogas`.
  AC: opening a yoga shows that selected yoga's detail; unrelated yogas do not
  reuse Gajakesari copy.
  Evidence: learning sheet now receives selected yoga detail instead of using
  fixed Gajakesari content.

- [x] **Mobile scrollbar sticks hidden** — P3.
  Routes: all `/m/*`.
  AC: normal mobile interaction does not show persistent horizontal or vertical
  scrollbar sticks.
  Evidence: mobile global scrollbar suppression is defined in
  `styles-mobile.scss`.

- [x] **Calendar red dots** — P3.
  Route: `/m/calendar`.
  AC: red/event dots are not shown for every personal signal; month dots
  reflect festival counts only.
  Evidence: calendar `eventCount` derives from festival rows.

- [x] **Ask history icon visibility in dark mode** — P3.
  Route: `/m/ask`.
  AC: history icon remains visible in dark mode.
  Evidence: dark-mode icon filter applied for Ask history control.

- [x] **Light-mode top status/signal bar visibility** — P2.
  Routes: `/m/today`, `/m/settings`, `/m/calendar`, `/m/chart`, `/m/ask`.
  AC: Android status bar and top app area remain readable in light mode across
  shell and overlay states.
  Evidence: installed APK verified on connected Android phone
  (`R5CY11Y5W7L`) on 2026-08-04; Capacitor StatusBar bridge now follows the
  app theme and the Today shell shows dark system icons on the light surface.

- [x] **Calendar day selection routes to the selected date** — P1.
  Routes: `/m/calendar`, `/m/calendar/day`.
  AC: tapping different dates opens the matching day detail; query-param
  changes do not leave the previous date visible.
  Evidence: installed APK verified on connected Android phone
  (`R5CY11Y5W7L`) on 2026-08-04 with August 5 and August 12 opening distinct
  detail pages.

- [x] **Divisional chart planet tap targets** — P1.
  Routes: `/m/chart/full`, `/m/chart/vargas`.
  AC: planet markers in divisional charts are individually tappable and open
  the correct planet detail sheet.
  Evidence: installed APK verified on connected Android phone
  (`R5CY11Y5W7L`) on 2026-08-04; tapping Venus in D9/Navamsa opened
  "Venus in Cancer" detail.

### Partially covered — requires verification or deeper work

- [~] **Notifications toggle is still not real push delivery** — P1.
  Routes: `/m/settings/notifications`, `/m/notifications`.
  AC to close: notification choices persist; OS permission state is visible;
  denied state has recovery actions; real push registration/device-token
  delivery is either implemented or explicitly product-deferred in the UI.
  Current state: local preferences exist and native/web copy no longer calls the
  APK a browser preview, but push delivery is not complete.

- [~] **Settings option glitch screen** — P1.
  Routes: all `/m/settings/*`.
  AC to close: opening every settings option on Android shows no blank,
  mixed-theme, or flash-of-wrong-screen state; Android back returns cleanly.
  Current state: mobile route animation was removed, but native sweep is still
  required.

- [~] **Today score weighting and layman explanation** — P1.
  Route: `/m/today`.
  AC to close: score gives primary weight to Chandrabala/Tarabala; the sheet
  explains why the day is good/caution/avoid in plain language; Guided and
  Balanced users do not see raw technical tally as the main explanation.
  Current state: score weighting and main reason text are improved; content QA
  against live varied days is still required.

- [~] **Settings conventions are wired but need full proof** — P1.
  Routes: `/m/settings/conventions`, `/m/chart`, `/m/chart/full`,
  `/m/chart/vargas`.
  AC to close: chart style persists locally and to cloud; D1 and every
  divisional chart inherit the selected style; ayanamsha/node changes
  invalidate affected computations; Settings summary remains current and not
  misleading.
  Current state: chart-style signals are consumed by full/varga/hub charts and
  sync conflict protection was added; full native verification remains.

- [~] **Dosha source display** — P2.
  Route: `/m/chart/yogas`.
  AC to close: every dosha shows authoritative source/provenance or explicitly
  says source unavailable; no silent source gaps remain.
  Current state: missing source visibility improved; source completeness remains
  open.

- [~] **Strength/Ashtakavarga interpretation** — P2.
  Route: `/m/chart/strength`.
  AC to close: Ashtakavarga, Shadbala, Jaimini and strengths explain
  "what this means for you" without repeating generic text.
  Current state: Shadbala, Ashtakavarga and Jaimini now show derived plain
  interpretation; deeper source-specific interpretation remains.

- [~] **Transits and Gochara usefulness** — P1.
  Routes: `/m/transits`, `/m/transits/full`.
  AC to close: each transit explains affected life area, practical effect,
  caution/support, timing and source; Guided/Balanced avoid technical dumping.
  Current state: domain and planet rows now include practical "use/watch" lines
  before evidence; deeper content QA against varied charts remains.

- [~] **Tab latency and recomputation** — P1.
  Routes: `/m/today`, `/m/calendar`, `/m/chart*`.
  AC to close: after profile creation/edit, major tab payloads warm once and
  reuse cached/stale data; tab entry does not recompute unnecessarily; explicit
  refresh is visible.
  Current state: caches exist and Calendar no longer auto-refreshes from cached
  entry; profile-level precompute/loading orchestration is still open.

- [~] **Readings wired with Ask** — P2.
  Routes: `/m/readings`, `/m/ask`.
  AC to close: reading CTA passes reading id/context to Ask; Ask placeholder
  acknowledges the selected reading; future real Ask can continue from that
  context.
  Current state: CTA exists; context continuity still needs proof and likely
  stronger query parameters.

- [~] **Compatibility full detail quality** — P1.
  Routes: `/m/compat/results`, `/m/compat/results/detail`.
  AC to close: full detail explains result, strengths, cautions,
  cancellations, timing and practical guidance; not just raw Gun Milan rows.
  Current state: score interpretation and caution/strength rows exist; richer
  explanation remains.

### Open

- [ ] **UX/font audit** — P2.
  Routes: all `/m/*`.
  AC: inventory actual font families; define approved mobile fonts; confirm
  `SIDDHA` brand uses Samarkan only where intentional; remove accidental mixed
  typography and non-Figma text styling.

- [ ] **Dasha plus Gocharam interpretation** — P1.
  Routes: `/m/chart/periods`, `/m/transits`.
  AC: active dasha stack explains current effect in plain language and relates
  it to active gocharam; Practitioner receives technical provenance.
  Current state: active dasha stack now explains the current chapter and
  practical use; direct dasha-to-gocharam synthesis remains open.

- [~] **Yogini interpretation** — P2.
  Route: `/m/chart/periods`.
  AC: Yogini periods show meaning, timing, effect and source/provenance; not
  just period table data.
  Current state: active Yogini and period rows now have plain meanings; stronger
  provenance and interaction with Vimshottari remain open.

- [ ] **Life domains interpretation** — P1.
  Routes: Chart, Readings and Compatibility surfaces that show life domains.
  AC: "what this means for you" sections are specific, non-repetitive and
  derived from chart/dasha/transit context.

- [ ] **Notes underline verification/fix** — P3.
  Route: `/m/notes`.
  AC: Notes UI has no unintended underline; local-draft behavior remains honest.

- [ ] **Final full mobile UI/UX audit** — P0 for release readiness.
  Routes: all `/m/*`.
  AC: 375 x 812 browser screenshots plus Android screenshots; light/dark;
  Guided/Balanced/Practitioner; route inventory; broken CTA table; prioritized
  backlog; results recorded in `docs/mobile_ui_regression_audit.md`.

## Definition of done for any item above

Do not check an item off because its Figma layout renders. Per the
2026-07-27 audit's §11: it must be reachable in the relevant persona
mode(s), preserve the same calculation truth as every other mode, map every
visible field to a real endpoint/key (no fixture text), define its loading/
empty/error/offline state, and — where it touches a safety-relevant surface
(death/health/legal/financial framing, dosha display) — carry the same
refer-out and non-fatalistic rules as the rest of the app.
