# Reliable Native Core Architecture

Date: 2026-08-14

Status: web-storage pilot implemented; encrypted native Today/Calendar repository implemented on `codex-native-secure-cache`, physical-device privacy proof pending

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

### Decision: conditional go, separate proof PR

Approve `@capacitor-community/sqlite` 8.1.1 as the preferred native repository
candidate, but do not add it to this pilot PR. Package compatibility is not
proof that encrypted persistence is correctly configured. A dedicated
dependency/native-project PR must pass every gate below before the application
stores private profile context or queued writes in it.

1. Generate a cryptographically random installation secret on device. Never
   hardcode a passphrase in Angular, `capacitor.config`, source control, build
   variables, or a remotely delivered configuration.
2. Store/use the secret through the plugin's native secure-secret path backed
   by iOS Keychain and Android Keystore. JavaScript may provide a newly
   generated secret during initialization but must not persist or log it.
3. Open the database with encryption enabled and prove with native tests that
   the resulting file cannot be opened as plaintext SQLite.
4. Exclude the database and secret material from Android cloud backup/device
   transfer and iOS backup unless a separately reviewed encrypted-restore model
   exists. Verify the built manifests and an actual backup/restore attempt.
5. Run schema upgrades transactionally. On failure, disposable cache tables may
   be rebuilt; confirmed profile facts and queued mutations must never be
   silently discarded or downgraded to plaintext storage.
6. Logout/account deletion cancels repository work, closes connections,
   removes that account's rows, compacts or deletes the database as policy
   requires, and clears the installation secret only after encrypted data is no
   longer needed. A second account must not inherit the first account's rows.
7. If secure-secret initialization or encrypted open fails, private durable
   features become unavailable with an honest recovery state. There is no
   `localStorage`, Preferences, or unencrypted-SQLite fallback for Profile
   Context Ledger facts, Ask memory, reports, notes, or queued writes.
8. Release/legal acknowledges SQLCipher encryption export-classification and
   reporting obligations before store submission.

The first native proof stores only disposable Today/Calendar cache envelopes.
Profile Context Ledger and offline mutation queues remain disabled until key
rotation, recovery, conflict handling, and deletion semantics pass a second
privacy review.

### Native proof matrix

| Scenario | Required evidence |
|---|---|
| Fresh Android install | Random secret created; encrypted DB opens; cache survives process death |
| Fresh iOS install | Random secret created; encrypted DB opens; cache survives process death |
| App upgrade with schema change | Upgrade commits atomically; rollback/recovery leaves app usable |
| Wrong/missing secret | No plaintext fallback; explicit recoverable state; no private payload logged |
| Logout A -> login B | A rows unavailable before B renders; no shared front-cache or open connection |
| Uninstall/reinstall | No orphaned readable database; initialization behavior documented per platform |
| Backup/device transfer | Database and secret do not produce a restorable mismatched or readable copy |
| Storage full/corrupt cache | Cache rebuild succeeds without affecting auth or server-owned data |
| Background/foreground | Connection lifecycle is stable; no duplicate handles or stale-account reads |
| Encryption inspection | Native artifact/file check demonstrates SQLCipher, not header-only configuration |

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

### Implemented 2026-08-14

- Canonical cache envelopes now scope Today and Calendar by authenticated
  account, profile, profile revision, date/range, place, timezone,
  conventions, and practitioner payload depth.
- The first runtime repository uses WebView storage behind
  `ResourceCacheService`; legacy unscoped Today/Calendar entries are deleted
  and never reused.
- Fresh entries render without a redundant route-load request. Stale entries
  render immediately with an explicit notice and refresh once in the
  background. Expired or corrupt entries are removed.
- Profile edits/deletes/logout invalidate both persistent rows and in-memory
  request maps. Late cached data cannot satisfy another account or profile.
- Unit tests cover account, profile revision, location, convention and persona
  isolation. The Angular suite (61 tests), production build, and 375x812 Today
  and Calendar empty-state visual checks pass.

### Native encrypted repository implemented 2026-08-14

- `@capacitor-community/sqlite` 8.1.1 is wired into Android and iOS with
  encryption enabled. A cryptographically random 256-bit installation secret
  is created once and stored through the plugin's Android Keystore/iOS Keychain
  secret path; it is never written to Angular storage, configuration, or logs.
- Native startup opens only an encrypted SQLCipher connection and verifies
  `isDatabaseEncrypted()` before hydrating memory. A failed secret, connection,
  or encryption check leaves durable caching unavailable and never falls back
  to WebView `localStorage`.
- Capacitor bridge logging is disabled for every build configuration because
  native plugin method arguments contain the serialized cache envelope. This
  was caught during the first Android device proof before release.
- The cache service blocks bootstrap until persistence hydration completes,
  then preserves its synchronous memory read API. Writes and account/profile
  deletions are serialized so a late write cannot overtake logout cleanup.
- The first native table contains only disposable Today/Calendar envelopes,
  keyed and indexed by account/profile identity. Profile Context Ledger facts,
  Ask memory, reports, notes, and offline mutations remain out of scope.
- Android `allowBackup=false` remains enforced. The SQLite iOS implementation
  marks its configured `Library/CapacitorDatabase` directory excluded from
  iCloud backup when creating it.
- Verified: 67/67 Angular tests; production Angular build; Capacitor sync for
  both targets; Android debug APK build containing `libsqlcipher.so` for all
  packaged ABIs; unsigned iOS simulator build linking SQLCipher 4.17.0.

Still required before merge/release approval: physical Android and iOS runs
covering process death, logout A -> login B, wrong/missing secret, backup/device
transfer, and direct inspection that the on-device database file is not readable
as plaintext SQLite. Encryption export classification also remains a release
owner/legal acknowledgement, not an engineering checkbox.

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
| Civil midnight before local sunrise | Keep the Vedic day that began at the previous sunrise once the backend supplies its authoritative interval; do not derive this from device midnight |
| Corrupt local row | row is quarantined/deleted; network recovery succeeds; app does not crash |
| Storage full | existing cache remains usable; failed write is observable and non-fatal |

### Astrological validity contract required from the backend

The current `/context/{profile_id}/daily` response is civil-date keyed and does
not expose an authoritative Vedic-day interval. The client must not approximate
sunrise from a display string or device clock. Before the Today cache policy is
considered astrologically complete, the backend must return:

```json
{
  "engine_version": "daily-guidance-...",
  "valid_from": "2026-08-14T06:03:00+05:30",
  "valid_until": "2026-08-15T06:04:00+05:30",
  "day_definition": "sunrise_to_next_sunrise"
}
```

For a pre-sunrise request, the backend selects the Vedic day that began at the
previous sunrise. Once available, `valid_from` (or a stable Vedic-day ID) joins
the cache identity and `valid_until` caps `expiresAt`; the fixed 36-hour policy
remains only a defensive upper bound. Calendar/festival responses likewise
need an `engine_version`/`dataset_version` so rule deployments invalidate old
projections independently of `profile.updated_at`.

Muhurta and transit resources require response-owned `valid_until` boundaries
at the end of the represented window. A generic TTL may be shorter, but never
longer. This pilot does not yet cache those resources and must not extend the
generic Today/Calendar adapter to them without that contract.

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
