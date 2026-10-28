# iOS builds to TestFlight on every merge

Status: canonical. How main reaches TestFlight without the Mac (the `ios` job
in `.github/workflows/ship.yml`). The rest of the Ship workflow is in
[ship_from_github.md](ship_from_github.md).

## What happens on a merge

When CI is green on main and the merge touched `ui/` (not `ui/android`,
`ui/e2e` or specs), the **iOS build to TestFlight** job runs on a GitHub macOS
runner with the newest Xcode 26, after the server deploy:

1. Build number = commit count, the same number the AAB gets. If App Store
   Connect already holds that build or a higher one (the Mac uploaded it), the
   job says *skipped* and succeeds.
2. `npm ci`, `version:sync`, the production web build, `npx cap sync ios`.
3. The CI distribution certificate goes into a throwaway keychain.
   `scripts/asc.py profile` finds an active App Store profile for
   `app.asksiddha.mobile` with that certificate, or makes one, and does the
   same for the home-screen widget extension's App ID
   `app.asksiddha.mobile.widgets` (`--bundle`). It looks every time because
   Apple invalidates a profile whenever the App ID's capabilities change. Both
   App IDs carry the App Group `group.app.asksiddha.mobile`, set up by hand in
   Apple Developer (2026-10-28): Apple's API can't create App Groups.
4. In that checkout only, the App and SiddhaWidgets targets' Release settings
   switch from automatic to manual signing with those profiles, and
   `aps-environment` becomes `production`. Nothing is committed back.
5. Archive, export the IPA (kept 30 days as a run artifact), upload with
   `xcrun altool` using the App Store Connect API key.

Apple then processes the build (about 10 to 30 minutes). The internal group
**Siddha Team** has automatic distribution, so it appears on those phones by
itself.

GitHub's macOS runners are free for this repository because it is public.

## What it never does

- **Submit for App Review or release to the App Store.** `scripts/asc.py` has
  no review, release or tester calls, and a test checks that it stays that way.
  A store release is done in App Store Connect on Hawk's word.
- **Give a build to the external group** ("Friends and family"). Add the build
  to that group in App Store Connect › TestFlight. A new build may need Beta
  App Review again; Apple decides.
- **Touch the Mac's signing.** The Mac keeps Xcode's automatic signing and its
  own certificate. GitHub has a separate Apple Distribution certificate made
  only for it, so revoking one never breaks the other.

A pull request that edits `ship.yml` or `scripts/asc.py` runs the job as a dry
run: an unsigned archive, no secrets, nothing uploaded. That proves the app
still builds on a clean Mac.

## One-time setup

### Hawk, in App Store Connect (about five minutes)

The API key lets GitHub talk to Apple as the team, the way the Play service
account does for Google.

1. Open [App Store Connect](https://appstoreconnect.apple.com) › **Users and
   Access** › **Integrations** › **App Store Connect API**.
2. If it shows **Request Access**, click it and accept the terms. Only the
   Account Holder can do this.
3. Under **Team Keys**, click **+** (Generate API Key). Name it `GitHub Ship`.
   Access: **Admin**. Admin is needed because the setup creates GitHub's own
   distribution certificate; App Manager cannot.
4. Click **Download** next to the new key. Apple allows this **once**. The file
   is named `AuthKey_XXXXXXXXXX.p8`.
5. Note the **Issuer ID** shown above the list of keys (a long ID with dashes).
6. In Finder, move the `.p8` from Downloads into your home folder (the Mac's
   Terminal cannot read Downloads).

Never paste the `.p8` contents into a chat.

### The Mac (one command)

From the repo folder, signed in to `gh` as repos-3sds:

```bash
bash scripts/ci/setup_ios_ship.sh ~/AuthKey_XXXXXXXXXX.p8 <issuer-id>
```

It checks the key, creates GitHub's Apple Distribution certificate through the
API (the private key never leaves a temporary folder), confirms a profile can
be made for it, and stores five GitHub secrets without printing them:

| Secret | What it is |
| --- | --- |
| `ASC_KEY_ID` | the API key's ID |
| `ASC_ISSUER_ID` | the team's issuer ID |
| `ASC_KEY_P8_B64` | the `.p8`, base64 |
| `IOS_DIST_P12_B64` | GitHub's distribution certificate and key, base64 |
| `IOS_DIST_P12_PASSWORD` | a random password for that p12 |

Run it once. Running it again makes another certificate, and Apple allows only
a few; if it reports too many, revoke an unused one in Certificates, Identifiers
& Profiles. Then run *Actions › Ship › Run workflow* on main with **ship
everything** ticked to prove the whole path.

Until the setup is done, the job notes *not set up yet* and skips, so the
server and Android keep shipping green.

## When it fails

The run summary names the step.

- **A secret is not set**: run the setup again (after revoking the certificate
  it made, if the p12 secret is the missing one).
- **No distribution certificate with serial …**: someone revoked GitHub's
  certificate. Revoke-and-rerun the setup.
- **Archive fails but the Mac builds**: usually a plugin added without
  `npx cap update` (see [native_builds.md](native_builds.md)), or a new Xcode
  on the runner. The dry run on the PR that changed it shows the same error.
- **altool says the build number was already used**: the Mac uploaded the same
  commit while this run was building. Nothing to fix.

Certificates last a year. When GitHub's expires (about October 2027), revoke it
and run the setup again; nothing else changes.
