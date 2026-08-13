# Siddha Commercial Entitlement Architecture

Date: 2026-08-14

Status: product and engineering contract proposal; no purchasing or gating is live

Owner: Codex

Required reviewers: product owner for packaging/pricing; Claude for backend enforcement; release owner for App Store/Play configuration; privacy reviewer for Family

## Executive Decision

Siddha should launch with four product plans:

- **Free** — a trustworthy daily guide and one complete personal foundation.
- **Plus** — deeper individual guidance, more profiles, richer planning, and
  materially higher Ask usage.
- **Pro** — advanced study/practitioner workflow, many managed profiles,
  professional reports, notes, comparison, and high usage.
- **Family** — shared payment with private member spaces, dependent profiles,
  family-aware planning, and explicit sharing controls.

Personas remain **Guided, Balanced, and Practitioner** presentation modes.
They are not plans. Paying never changes chart facts or safety; it changes
feature breadth, volume, workflow, storage, and report capability.

Do not ship the existing Subscription screen as a simulated purchase surface.
Until backend entitlement verification, store products, restore, webhook
handling, and downgrade behavior exist, it remains informational only.

## Product Principles

1. **Truth is not premium.** The same computation, conventions, source
   integrity, safety boundaries, and correction mechanisms apply to all plans.
2. **Reliability is not premium.** Session persistence, current-location
   correctness, profile isolation, stale/offline state labels, and basic device
   caching are quality requirements for every reader.
3. **Transparency is not premium.** Every answer may show what context was used,
   source references, confidence, and safety limitations.
4. **Monetize depth, volume, continuity, and workflow.** Rich interpretation,
   extended history, planning tools, exports, many profiles, collaboration,
   practitioner workbench, and higher Ask usage are legitimate paid value.
5. **No fear conversion.** Never gate a “dosha removal,” safety reassurance,
   account deletion, or critical explanation behind payment.
6. **Server authority.** The app may cache entitlements for resilience, but the
   backend decides access and quotas. UI hiding is not enforcement.
7. **Graceful downgrade.** Data is never destroyed merely because payment ends.
   Creation and premium processing may pause; existing private data remains
   exportable/deletable and becomes read-only where necessary.
8. **Family payment is not family surveillance.** Shared entitlement does not
   grant the purchaser access to another adult's chart, Ask history, profile
   memory, or reports.

## Current Repository Reality

As of this document:

- `/m/subscription` exists as a disabled/informational screen.
- No billing SDK, StoreKit/Play bridge, product catalog, receipt verification,
  webhook processor, subscription table, entitlement resolver, usage ledger,
  or server-side profile limit exists.
- Personas exist and affect presentation; they must not be repurposed as plan
  gates.
- Multiple profiles exist, but limits and Family ownership semantics do not.
- Ask has server persistence but no commercial quota authority.
- Reports/sharing are not sufficiently complete to sell.
- Local caches exist, but reliability behavior is not an entitlement.

Therefore every plan below is a target contract, not implemented behavior.

## Market Signals

The benchmark is directional, not a mandate to copy competitors.

| Product | Verified signal | Implication for Siddha |
|---|---|---|
| CHANI | Free daily horoscopes, Moon/current-sky information and basic birth-chart overview; premium unlocks detailed chart content. US App Store lists $11.99 monthly and $107.99 annual at time of review. | Preserve daily/basic chart value free; charge for depth and an ongoing content/guidance relationship. |
| AstroSage Kundli | Markets Kundli, matching, Panchang and many systems as free. | A Vedic product cannot make every basic calculation premium and remain competitive. |
| AstroSage Dhruv | Practitioner product monetizes unlimited charts, detailed printable reports, cloud storage, notes, and branding; official page lists ₹999 monthly/₹9,999 yearly at review time. | Pro value should be workflow, scale, reports, storage and practitioner tools, not merely a different color theme. |
| Co-Star | Uses auto-renewing external-store subscriptions and trials. | Siddha needs complete trial, renewal, cancellation, price-change and restore states before selling. |
| Apple/Google stores | Require real transaction lifecycle handling. Google recommends backend verification/acknowledgment and prohibits granting pending purchases. Apple requires restore support and exposes revocation/Family Sharing lifecycle. | Entitlements must be derived from verified store/server events, never a local boolean. |

Primary references:

- [CHANI App Store listing](https://apps.apple.com/us/app/chani-your-astrology-guide/id1532791252)
- [AstroSage Kundli feature page](https://www.astrosage.com/mobileapps/astrosage-kundli-best-astrology-app-by-astrosage.asp)
- [AstroSage Dhruv plans](https://www.astrosage.com/dhruv/)
- [AstroSage Cloud plan boundaries](https://www.astrosage.com/controls/i_terms.asp)
- [Co-Star subscription terms](https://www.costarastrology.com/terms)
- [Google Play Billing integration](https://developer.android.com/google/play/billing/integrate)
- [Google Play backend integration](https://developer.android.com/google/play/billing/backend)
- [Apple purchase restoration](https://developer.apple.com/documentation/storekit/restoring-purchased-products)
- [Apple Family Sharing](https://developer.apple.com/documentation/storekit/supporting-family-sharing-in-your-app)

Prices are localized and change. Competitor prices are research observations,
not proposed Siddha prices and must not be hardcoded into product copy.

## Proposed Launch Entitlements

Limits are launch hypotheses and must be remotely configurable. The product
surface should describe benefits, while exact counters come from the server.

| Capability | Free | Plus | Pro | Family |
|---|---|---|---|---|
| Account seats | 1 | 1 | 1 | Up to 6 members |
| Profiles | 1 | 3 | 25 managed profiles | 6 private member profiles + up to 6 dependents |
| Guided/Balanced/Practitioner presentation | All | All | All | All |
| Today and core Panchanga | Full | Full | Full | Full per member |
| D1 chart and birth signature | Full | Full | Full | Full |
| Core Calendar and location correctness | Full | Full | Full | Full |
| Essential festivals | Full | Full | Full | Full |
| Full festival packs and custom filters | Preview | Full | Full | Full per member |
| Vargas | D1 + selected introduction | Full standard set | Full set + advanced comparison | Full standard set |
| Dashas | Current stack and explanation | Full five-level navigation | Full + comparison/export | Full five-level navigation |
| Strengths, Yogas, Doshas | Essential summary with sources | Full interpretation | Full technical tables and provenance | Full interpretation |
| Transits/Gochara | Current summary | Full timeline/domain detail | Full technical parameters/export | Full timeline/domain detail |
| Remedies | Safe essential recommendations | Personal plans, reminders, audio | Custom practice plans and client notes | Per-member plans; no forced sharing |
| Muhurta | Limited standard searches | Full personal searches/save | Advanced filters, comparison, report | Shared event planning with private context |
| Compatibility | One saved comparison | Up to 10 saved comparisons | High-volume comparison/report | Family/relationship comparisons by consent |
| Ask grounded answers per billing month | 5 | 60 | 300 | 60/member + 120 shared pool |
| Ask follow-up threads | 7-day history | 12-month history | Full retained history subject to policy | 12 months per private member |
| Profile Context Ledger | User controls and safety always | Full continuity | Full continuity + professional notes kept separate | Full private ledger per member |
| Audio | Today and accessibility essentials | Full readings/practices | Full + export-ready scripts | Full per member |
| Reports | One basic personal report | Detailed personal/share report | Practitioner templates, batch/export, optional branding | Family overview only with explicit consent |
| Notes | Basic personal notes | Extended notes | Structured practitioner notes | Private personal notes |
| Offline resilience/cache | Full reliability baseline | Full | Full | Full |
| Downloaded offline library/history | Limited current content | Extended | Extended managed profiles | Per-member extended |
| Priority computation | No artificial degradation | Standard priority | Higher concurrency/fair-use ceiling | Standard per member |
| Support | Self-service | Standard | Priority practitioner support | Standard family support |

### Important Packaging Corrections

- `Practitioner` mode stays selectable on Free. Pro unlocks advanced
  practitioner **workflow**, not vocabulary preference.
- Source citations and “Why this reading?” stay available on Free.
- Free Ask refusals, clarification turns, failed generation, and verification
  failures do not consume quota.
- Viewing existing data, correcting profile details, deleting/exporting data,
  restoring purchases, and safety resources never consume quota.
- Basic device caching and offline error handling are not Plus features.

## Ask Usage Model

### Billable unit

One credit is consumed only when the server persists a successfully verified
`answered` assistant turn. These do not consume credits:

- `refer_out`
- `clarification_needed`
- `domain_not_ready`
- `generation_failed`
- `verification_failed`
- validation probes and their answers
- retries caused by transport failure before persistence

Follow-ups consume one credit when they produce another verified answer.
Editing and resubmitting a question creates a new attempted turn, but only its
successful persisted answer is charged.

### Enforcement

The orchestrator must reserve a quota unit atomically before expensive model
generation, then commit or release it with the answer transaction. This avoids
parallel requests exceeding limits and prevents failed turns from charging.
The client displays server-provided `remaining`, `resets_at`, and fair-use
status; it never calculates authority locally.

### Exhausted state

Readers may still open history, Today, charts, Calendar, sources and safety
information. Ask shows reset time and plan options without fear language.
Emergency/medical/legal/financial refer-out guidance remains reachable without
an Ask credit because routing happens before quota consumption.

## Canonical Entitlement Model

Products, plans, and entitlements are different objects:

```text
store product/base plan/offer
  -> verified subscription grant
  -> Siddha plan assignment
  -> resolved entitlement set + limits
  -> usage ledger
  -> feature decision
```

Recommended response:

```json
{
  "account_id": "uuid",
  "plan": "plus",
  "status": "active",
  "source": "google_play",
  "effective_at": "2026-08-14T00:00:00Z",
  "expires_at": "2026-09-14T00:00:00Z",
  "grace_ends_at": null,
  "revision": 42,
  "entitlements": {
    "profiles.max": 3,
    "ask.answers.monthly": 60,
    "reports.detailed": true,
    "vargas.full": true
  },
  "usage": {
    "ask.answers.monthly": {
      "used": 12,
      "remaining": 48,
      "resets_at": "2026-09-01T00:00:00Z"
    }
  }
}
```

Never make mobile code branch on product IDs. It asks whether an entitlement
exists or a limit permits an action. Store product mappings remain server-side
configuration.

## Backend Data Model

Recommended entities:

### `billing_accounts`

- `id`, `owner_user_id`, `kind` (`individual`/`family`)
- `created_at`, `updated_at`

### `subscription_grants`

- `id`, `billing_account_id`, `provider`, `provider_product_id`
- provider transaction/purchase-token identity
- `state` (`pending`, `active`, `grace`, `paused`, `expired`, `revoked`)
- `starts_at`, `renews_at`, `expires_at`, `grace_ends_at`
- `verified_at`, `last_event_at`, raw-provider-reference hash
- unique provider transaction/token constraints for idempotency

### `plan_assignments`

- `billing_account_id`, `plan_code`, `source_grant_id`
- `effective_at`, `ends_at`, `revision`

### `family_memberships`

- `billing_account_id`, `user_id`, `role`, `status`
- invite identity, accepted/revoked timestamps
- no automatic profile-reading permission

### `entitlement_overrides`

- support/admin grants with reason, actor, expiry and audit trail

### `usage_buckets`

- billing account/user/profile scope as required
- entitlement key, period start/end, reserved, consumed
- version and idempotency key

Store raw receipts/tokens encrypted or in a restricted billing store. Never
expose them to the Angular application or logs.

## Entitlement Resolution

Priority order:

1. Safety/privacy/account-management baseline (always available).
2. Active verified subscription grant.
3. Grace-period policy.
4. Time-bounded support/admin override.
5. Free defaults.

The resolver returns an immutable snapshot with a revision. Every gated backend
operation checks that snapshot server-side. The mobile app caches it only to
render quickly and must refresh on foreground, purchase completion, restore,
profile creation, and server notification.

## Purchase Architecture

```text
mobile requests localized products from StoreKit/Play
  -> reader confirms native purchase sheet
  -> client sends transaction/purchase token to Siddha backend
  -> backend verifies with Apple/Google
  -> backend writes idempotent grant and acknowledges where required
  -> entitlement resolver publishes new revision
  -> client refreshes entitlement snapshot
```

Provider server notifications update renewals, refunds, billing retry, grace,
pause, expiration, revocation and Family Sharing changes even when the app is
closed.

### Platform rules

- Google: grant only `PURCHASED`, not `PENDING`; verify and preferably
  acknowledge on the backend; process RTDN lifecycle events.
- Apple: use verified StoreKit transactions/App Store Server notifications;
  provide an explicit Restore Purchases action; handle revocation.
- Do not automatically trigger an interactive restore at launch.
- Web purchases, if later offered, map into the same server entitlement model.

RevenueCat or another service may reduce platform plumbing, but it does not
replace Siddha's server-side feature/usage resolver, Family privacy, or profile
limits. Vendor choice is a separate ADR.

## Lifecycle State Machine

| State | Access behavior |
|---|---|
| Free | Free entitlements |
| Purchase pending/deferred | Keep current plan; show pending; no premature unlock |
| Active | Resolve paid plan immediately after backend verification |
| Canceled, period active | Keep access through paid-through date; show renewal-off |
| Billing retry/grace | Keep paid access during configured grace; show discreet payment action |
| Paused | Follow provider dates; usually retain read access, pause paid generation |
| Expired | Free creation/generation limits; paid data retained read-only/exportable |
| Refunded/revoked | Re-resolve promptly; no destructive deletion |
| Upgrade | Unlock after verified effective transaction; platform proration applies |
| Downgrade | Keep current plan until effective date; preview future limits |
| Restore | Re-verify provider ownership, then refresh server snapshot |

## Profile Limits And Downgrade

- Profile creation is enforced transactionally on the backend.
- Existing profiles over the new limit are not deleted.
- On downgrade, the reader chooses which profiles stay active; others become
  archived/read-only until the limit increases or a profile is deleted.
- The active profile cannot be silently archived.
- Ask generation, recalculation and new reports are disabled for archived
  over-limit profiles, but export/delete remain available.
- Family dependent profiles have an accountable guardian and age-appropriate
  privacy rules; adult profiles become independently owned when invited and
  accepted.

## Family Privacy Model

Family is a billing and optional collaboration container, not one shared
astrology database.

- Each adult member has a private user identity and private profile namespace.
- Organizer can see seat status and payment, not Ask threads, birth details,
  Profile Context Ledger facts, notes or reports.
- Sharing is per artifact/profile/domain, explicit, revocable and logged.
- Compatibility requires consent or a clearly managed dependent profile.
- A shared calendar event may expose event time/place without exposing the
  private chart factors used to evaluate it.
- Leaving a family removes paid access and shared grants, not the member's own
  account data.
- Apple Family Sharing is a store entitlement mechanism, not a substitute for
  Siddha Family membership/privacy. Google parity must be designed server-side.

## Feature-Gate UX

Use four states, not a generic paywall everywhere:

1. **Available** — normal control.
2. **Preview** — useful bounded sample with a clear depth/limit explanation.
3. **Limit reached** — preserve context and show reset/management options.
4. **Unavailable for plan** — explain the workflow value and route to plans.

Rules:

- Never navigate away before preserving the user's draft/date/profile context.
- Never show an upgrade wall after expensive computation has already run.
- Paywall copy names the capability, not a promised life outcome.
- One comparison screen, sourced from the entitlement matrix, prevents drift.
- Settings always includes Manage Subscription and Restore Purchases.
- Dark/light, safe areas, dynamic type, screen readers and native back behavior
  apply to purchase and restore surfaces.

## API Surface

```text
GET  /api/v1/billing/products?platform=android|ios
GET  /api/v1/entitlements
POST /api/v1/billing/google/verify
POST /api/v1/billing/apple/verify
POST /api/v1/billing/restore
GET  /api/v1/usage
POST /api/v1/usage/{key}/reserve       # internal service boundary preferred
POST /api/v1/family/invitations
POST /api/v1/family/invitations/{id}/accept
DELETE /api/v1/family/members/{id}
```

Provider webhooks/server notifications use separate authenticated endpoints
and are never exposed as ordinary user routes.

Gated APIs return structured errors:

```json
{
  "code": "entitlement_limit_reached",
  "entitlement": "ask.answers.monthly",
  "plan": "free",
  "remaining": 0,
  "resets_at": "2026-09-01T00:00:00Z",
  "upgrade_options": ["plus", "pro"]
}
```

## Admin And Operations

Admin needs read-only-first surfaces for:

- product-to-plan mapping health
- webhook lag/failures
- unacknowledged/pending purchases
- entitlement revision and source
- quota reservations stuck in-flight
- support overrides and audit history
- Family invitation/member status

Support may grant a time-bounded override but cannot fabricate provider
transactions, inspect private Ask/profile memory, or edit usage without an
audited reason.

## Telemetry And Finance

Track without reading private content:

- paywall viewed -> purchase sheet -> verified -> entitled funnel
- trial start/conversion/cancel
- restore success/failure
- entitlement resolution latency and stale snapshot rate
- Ask quota consumption/release and limit-hit rate
- profiles per plan and over-limit downgrade cases
- renewal, grace recovery, refund/revoke, webhook lag
- feature adoption and retained usage by plan

Do not log birth details, questions, answers, fact values, reports or store
tokens. Revenue reporting reconciles provider proceeds, taxes/refunds and the
internal grant ledger.

## Security And Abuse Controls

- Verify purchases server-side and bind them to an authenticated account.
- Use idempotency keys and unique provider transaction/token constraints.
- Hash or encrypt provider references; never use order ID alone as identity.
- Apply rate limits before model execution, but do not block safety routing.
- Prevent one store purchase from being claimed by unrelated Siddha accounts.
- Audit plan/override/membership changes.
- Fail closed for paid unlock when verification is unavailable; retain the last
  known valid entitlement through an explicitly bounded offline window.
- Never trust device clocks for expiry or quota reset.

## Acceptance Matrix

| Scenario | Required behavior |
|---|---|
| Free reader asks sixth successful question | No model generation; structured limit state with reset date; other app features remain available |
| Ask generation fails after reservation | Reservation released; no credit consumed |
| Refer-out question at zero credits | Safety response still returned; zero consumption |
| Android purchase is pending | No entitlement granted |
| Verified Android purchase | Backend grants and acknowledges; app refreshes entitlement |
| iOS reinstall | Restore Purchases recovers access without duplicate subscription |
| Cancellation | Paid access continues to paid-through date |
| Billing grace | Access follows configured grace; subtle payment action shown |
| Refund/revocation | Entitlement removed promptly; user data retained/exportable |
| Plus with three profiles downgrades to Free | Reader chooses one active; others read-only/archived, never deleted |
| Two concurrent profile creations at limit | Exactly one succeeds transactionally |
| Family organizer opens adult member | No private chart/history access without explicit grant |
| Adult leaves Family | Own data stays; paid/shared grants are removed |
| Offline launch with recently verified grant | Bounded cached access; stale state displayed if verification window expires |
| Client modifies local plan flag | Gated backend API still denies access |
| Persona changes Guided -> Practitioner | Entitlements unchanged; only presentation changes |
| Account deletion | Billing cancellation guidance plus complete Siddha data deletion; store records retained only as legally required |

## Delivery Epics

### CE-1: Product approval and economics

- Approve tier names, limits, launch countries, monthly/annual strategy, trials,
  Family definition and Pro audience.
- Model Ask cost, report cost, support cost, store commission, taxes/refunds and
  target gross margin.
- Replace provisional quotas only after cost/load tests.

### CE-2: Entitlement foundation

- Add plan/entitlement registry, billing account/grant/assignment/usage schema,
  resolver, structured denial errors and audit trail.
- Gate test-only sample endpoints before any store SDK.
- Golden tests prove UI and backend use the same registry.

### CE-3: Store integration

- Add reviewed Capacitor/native billing adapter.
- Configure products/base plans/offers in App Store Connect and Play Console.
- Add backend verification, acknowledgment, notifications and reconciliation.
- Implement purchase, pending, restore, grace, cancel and revoke UI.

### CE-4: Profile and Ask enforcement

- Transactional profile limits and downgrade archive selection.
- Atomic Ask reserve/commit/release tied to successful persisted answers.
- Plan-aware report/compatibility/Muhurta limits.

### CE-5: Family

- Billing account membership, invitations, private namespaces, dependent
  ownership, artifact sharing and revocation.
- Decide Apple Family Sharing only after cross-platform parity and privacy
  semantics are proven; enabling it cannot be undone in App Store Connect.

### CE-6: Commercial surfaces and launch

- Plan comparison, contextual upgrade, Manage Subscription, Restore Purchases,
  usage indicators, invoices/receipts links, support and account states.
- Store sandbox/license testing, webhook chaos tests, analytics/privacy review,
  support playbooks and staged rollout.

## Release Gates

1. Product owner approves entitlements and provisional limits.
2. Backend enforces every paid capability and quota; client-only gates are
   forbidden.
3. Apple/Google purchase verification, notifications, restore, pending, grace,
   refund and revocation pass sandbox/license tests.
4. Ask quota charges only verified persisted answers.
5. Downgrade never deletes profiles, threads, reports, notes or context facts.
6. Family privacy passes attacker-side cross-member tests.
7. Free users retain safety, sources, account controls, basic calculations,
   location correctness and reliability.
8. Purchase/paywall screens pass Android/iOS safe-area, dark/light, dynamic-type,
   screen-reader and native-back verification.
9. Finance reconciliation and support override auditing work before production.
10. Pricing is remotely/catalog driven and localized; no hardcoded price copy.

## Immediate Next Decision

Approve or revise the entitlement matrix before writing billing code. The
first engineering implementation should be **CE-2 Entitlement foundation**,
not a StoreKit/Play purchase button. That sequence gives the app one testable
server authority and prevents store products, frontend copy and API gates from
drifting into three competing definitions of “Pro.”
