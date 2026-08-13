# Reliable Native Core Architecture

Date: 2026-08-14

Status: proposed contract with an implementation-neutral cache-key prototype

Owner: Codex

Reviewers: Claude for backend contracts when available; Gemini for calendrical correctness; Qwen for adversarial tests

## Objective

Make Siddha behave like a dependable native application before expanding feature breadth. A returning reader should see the correct profile and location-specific data immediately, continue using previously loaded material offline, and never see another profile's private reading while the network refreshes.

This epic does not make cached astrology authoritative forever. The backend remains the source of truth. The native store is a versioned, privacy-scoped projection with explicit freshness and invalidation rules.

## Evidence From The Current App

The app already contains useful partial solutions:

- Supabase auth sessions use Capacitor Preferences and native foreground refresh.
- Today, Calendar, festivals, and full chart payloads have in-memory and `localStorage` caching.
- Today and Calendar include effective timezone and selected Panchanga place in request/cache parameters.
- Calendar and Calendar Day can show cached content when a refresh fails.
- Kundli edits call `VedicService.invalidate(profileId)`.

The implementation is not yet a coherent native data layer:

- Cache formats are private methods inside individual services.
- Stored payloads have no `storedAt`, `staleAt`, `expiresAt`, source, or schema metadata.
- Cache identity does not include the authenticated user or a server-issued profile/birth-data revision.
- `localStorage` is synchronous WebView storage, has limited capacity, and cannot support indexed eviction, migrations, transactions, or reliable per-user deletion.
- Detail endpoints are mostly memory-only and recompute after process death.
- There is no explicit offline/network state service.
- Logout does not have one cache repository it can ask to delete all private data for the signed-out user.
- Current location is a selected city preference, not verified device geolocation.
- No measurable latency, cache-hit, stale-hit, refresh-failure, or cross-profile-flash telemetry exists.

## Non-Negotiable Invariants

1. **No cross-account reuse.** Every private cache key contains the authenticated user UUID.
2. **No cross-profile reuse.** Every profile-derived key contains the profile UUID.
3. **No stale birth-chart reuse after edits.** Profile-derived entries carry a server-issued `profileRevision` or birth-details `updated_at` value.
4. **Current-place calculations are distinct from natal-place calculations.** Today, Calendar, festivals, transits, and Muhurta use current Panchanga place/timezone. Kundli and Vargas use birth place/timezone.
5. **Cached does not mean current.** Every entry is classified as fresh, stale-but-usable, or expired.
6. **Stale data is labelled.** The UI may render stale-but-usable data immediately, but must expose its age/place and refresh in the background.
7. **Expired data is not silently presented as current.** It may support an explicit offline fallback only when the screen identifies it as old.
8. **One in-flight request per identity.** Concurrent screen mounts share one refresh promise.
9. **A failed refresh never deletes a usable cached value.** Replacement is atomic after validation.
10. **Logout is deterministic.** Private cache rows, profile memories, transient Ask state, and pending writes for that user are deleted before the next account can render.
11. **Schema changes are migratable.** Cache schema versions are independent of API payload versions.
12. **Observability contains no birth data or reading prose.** Metrics use opaque user/profile hashes and resource names only.

## Cache Identity Contract

The canonical identity is:

```text
userId
+ profileId
+ resource
+ schemaVersion
+ profileRevision
+ date/date-range
+ timezone
+ city/nation
+ ayanamsha
+ nodeType
+ convention
+ variant/persona depth where payload shape differs
```

The new `resource-cache.ts` prototype builds this key in a fixed field order and rejects identities without account/profile scope. The key is shared by memory, web fallback, and the future native repository.

### Resource Policies

| Resource | Fresh | Stale usable | Hard expiry | Invalidate when |
|---|---:|---:|---:|---|
| Today guidance | 15 min | until local day ends | 36 hours | profile revision, current place/timezone, ayanamsha/node/convention |
| Calendar intelligence | 6 hours | 7 days | 45 days | profile revision, current place/timezone, convention, festival selection |
| Festival window | 24 hours | 14 days | 90 days | place, region/festival selection, backend dataset version |
| Natal chart/all Vargas | until profile changes | 30 days | 180 days | profile revision, ayanamsha, node type, chart-engine version |
| Dashas/strengths/yogas | until profile changes | 30 days | 180 days | profile revision, conventions, engine version |
| Transit/gochara | 30 min | 24 hours | 7 days | profile revision, current place/timezone, scan date/range |
| Ask thread metadata | immediate local projection | until sync | account retention policy | archive/delete/account deletion |
| Profile memory | server authoritative | explicit offline copy | policy-defined | correction, consent withdrawal, profile/account deletion |

These values are starting budgets, not hidden constants. They belong in a central policy registry and must be confirmed using production telemetry.

## Read Algorithm

```text
resolve authenticated user + active profile + profile revision
  -> build canonical identity
  -> read memory repository
  -> read native repository when memory misses
  -> classify freshness
     -> fresh: render, no blocking network call
     -> stale: render with stale metadata, refresh in background
     -> expired: show skeleton/offline-expired state, request network
  -> validate network response identity and payload
  -> atomically replace repository entry
  -> notify subscribers without remounting the route
```

The UI consumes a resource state, not a naked payload:

```ts
type ResourceState<T> =
  | { kind: 'loading'; previous?: T }
  | { kind: 'ready'; data: T; freshness: 'fresh' | 'stale'; updatedAt: number }
  | { kind: 'offline'; data?: T; expiredAt?: number }
  | { kind: 'error'; data?: T; retryable: boolean; message: string };
```

This prevents route-level skeleton flashes when usable data already exists.

## Native Storage Decision

### Recommendation

Use a repository abstraction with:

- **Native:** `@capacitor-community/sqlite` 8.x, using SQLCipher encryption for private profile/Ask-memory data.
- **Web preview:** IndexedDB adapter, not native SQLite's web emulation in the first release.
- **Memory:** small LRU front cache for synchronous repeat reads and request coalescing.

The current package registry reports `@capacitor-community/sqlite` 8.1.1 with a Capacitor Core `>=8.0.0` peer requirement, compatible with this app's Capacitor 8 line. Its official repository documents SQLCipher support on Android/iOS, migrations, transactions, and secure-secret APIs. It also warns that including SQLCipher can carry encryption export-compliance obligations. Therefore adding the dependency and enabling encryption require a separate reviewed PR, legal/release acknowledgement, and device proof on both platforms.

Do not store Supabase tokens in this database; Capacitor Preferences remains the auth SDK's storage adapter. Do not put full reading text in logs or analytics.

## Proposed Local Schema

```sql
CREATE TABLE resource_cache (
  cache_key TEXT PRIMARY KEY NOT NULL,
  user_id TEXT NOT NULL,
  profile_id TEXT NOT NULL,
  resource TEXT NOT NULL,
  schema_version INTEGER NOT NULL,
  profile_revision TEXT,
  payload_json TEXT NOT NULL,
  stored_at INTEGER NOT NULL,
  stale_at INTEGER NOT NULL,
  expires_at INTEGER NOT NULL,
  last_accessed_at INTEGER NOT NULL,
  byte_size INTEGER NOT NULL
);

CREATE INDEX resource_cache_owner ON resource_cache(user_id, profile_id);
CREATE INDEX resource_cache_expiry ON resource_cache(expires_at);
```

Separate tables should be used later for Profile Context Ledger facts and queued writes. Cache rows are disposable; profile memories are auditable user data and must not share cache retention semantics.

## Invalidation Matrix

| Event | Required action |
|---|---|
| Active profile switch | cancel/ignore old-profile requests; render only target-profile cache |
| Birth details edit | increment/receive profile revision; invalidate all natal and dependent resources for that profile |
| Current place change | invalidate Today, Calendar, festivals, transit and Muhurta identities; retain natal chart |
| Ayanamsha/node change | invalidate chart-derived resources; Calendar-only Panchanga data may remain if contract proves independence |
| Festival selection change | invalidate festival projection and Calendar composition, not core Panchanga days |
| Persona/tone change | invalidate only resources whose server payload actually differs by persona/tone |
| App background/resume | keep cached UI; refresh resources past `staleAt`; never clear session on network failure |
| Logout | cancel requests; clear memory; delete all rows owned by user; clear transient Ask/profile selection state |
| Account deletion | perform logout cleanup plus server deletion confirmation and local database compaction |

## Today + Calendar Pilot

### Slice A: Contract and instrumentation

- Land canonical key/envelope/freshness helpers and tests.
- Add a `ResourceRepository` interface and memory/web adapters.
- Record cache outcome (`memory_hit`, `disk_hit`, `stale_hit`, `miss`), read latency, fetch latency, payload bytes, and refresh outcome without PII.

### Slice B: Today

- Migrate Today behind the repository without changing its backend contract.
- Render cached data before network refresh.
- Show current place and stale timestamp when stale.
- Verify local-day rollover in the selected timezone.

### Slice C: Calendar and festivals

- Cache Panchanga intelligence separately from festival projection so changing festival filters does not recompute the astronomical month.
- Prefetch adjacent month after the visible month becomes interactive.
- Preserve selected date and visible month during refresh.
- Cancel or ignore responses from the previous profile/place.

### Slice D: Native database

- Add the reviewed SQLite dependency and schema migration.
- Migrate compatible `localStorage` Today/Calendar entries once with source `migration`, then delete legacy keys only after successful commit.
- Add LRU/size eviction and logout deletion.

## Acceptance Matrix

| Scenario | Expected result |
|---|---|
| Cold launch, cached Today | meaningful content visible within 300 ms; refresh does not blank it |
| Cold launch, cached Calendar | month grid visible within 300 ms; adjacent data refreshes quietly |
| No cache, fast network | progress state visible within 100 ms; one request only |
| Offline with stale cache | usable screen plus explicit stale/offline state and source place |
| Offline with no cache | purpose-built offline empty state; no endless spinner |
| Switch profile A -> B | no A content appears after switch begins; B cache/network only |
| Switch place Singapore -> Chennai | Today/Calendar keys change immediately; natal chart key does not |
| Edit birth details | old profile revision cannot satisfy any dependent read |
| Background 2 hours then resume | session remains; stale visible data refreshes once |
| Logout A, login B | B cannot read any A cache row, Ask draft, thread, or selected profile |
| Day boundary in selected timezone | Today key changes at that timezone's midnight, not device/UTC midnight |
| Corrupt local row | row is quarantined/deleted; network recovery succeeds; app does not crash |
| Storage full | existing cache remains usable; failed write is observable and non-fatal |

## Performance Budgets

- Memory cache read: p95 under 10 ms.
- Native database read: p95 under 75 ms for Today and Calendar index payloads.
- Cached first meaningful paint: p95 under 300 ms after route activation.
- UI reaction to profile/place switch: under 100 ms.
- No more than one matching network refresh in flight.
- Calendar initial payload should be bounded; practitioner detail may be lazy by selected day if backend contract permits.

## Work Division During Claude's Absence

### Codex

- Own this contract, repository interfaces, mobile adapters, Today/Calendar pilot, lifecycle UI, and Android/iOS evidence.
- Do not change Ask orchestration or backend schemas during Claude's active Ask migration.

### Gemini

- Produce golden Panchanga fixtures for at least Singapore, Chennai, Delhi, London, and New York across normal days, DST transitions, month boundaries, and a festival-dense period.
- Validate that location changes alter sunrise-dependent timings while natal calculations remain tied to birth place.

### Qwen

- Add attacker-oriented tests for A/B profile races, logout/login isolation, stale responses arriving after profile/place switches, corrupt rows, storage-full behavior, app kill/resume, and midnight rollover.
- Tests should be additive; production cache policy changes return to Codex for review.

### Claude, from 17 August

- Review API version/revision fields, server cache headers, invalidation semantics, and latency instrumentation.
- Decide whether Calendar can expose core Panchanga and festival projections independently without duplicate computation.

## Release Gates

The pilot cannot become the default path until:

1. Android and iOS device tests pass for cold start, resume, offline, profile switch, location switch, and logout/login.
2. No cross-profile flash appears in automated race tests or manual screen recording.
3. The cache can migrate and roll back without data loss or login failure.
4. Production telemetry shows hit rate and latency without collecting private content.
5. Claude reviews backend revision/invalidation assumptions.
6. Dependency and encryption compliance changes receive explicit review.

## Explicitly Deferred

- Profile Context Ledger and long-term predictive memory.
- Subscription entitlements and plan restrictions.
- Full Charts/Dashas/Explore cache migration.
- Automatic device geolocation and permission UX.
- Server-side Calendar decomposition.
- RAG/knowledge ingestion expansion.

Those are subsequent epics. The Reliable Native Core must establish privacy, identity, freshness, and lifecycle semantics first.

## References

- Capacitor Community SQLite repository and API documentation: https://github.com/capacitor-community/sqlite
- Capacitor Network plugin documentation: https://capacitorjs.com/docs/apis/network
- Capacitor Preferences plugin documentation: https://capacitorjs.com/docs/apis/preferences
