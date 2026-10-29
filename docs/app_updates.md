# Asking readers to update the app

Status: canonical. How a phone on an older build is told to update: on
launch, by reminder push, and, only when a build is marked required, by a
full-screen block.

## What the reader sees

| The phone's build | On launch | Pushes |
| --- | --- | --- |
| the latest, or newer (internal testers) | nothing | none |
| older than `latest_build` | sheet: "A new version of Siddha is ready", **Update now** / **Later** (Later hides it for a day) | first 6 hours after release, then after 2, 4, 7 and 7 days; five at most |
| older than `required_build`, or older than `latest_build` once `block_after_days` have passed | full screen: "Please update Siddha", **Update now** / **I have updated**; nothing else in the app can be used | every 2 days, eight at most |

- **Update now** on Android runs Play's own update screen (InAppUpdatePlugin),
  and opens the Play listing if Play cannot. On Android the sheet only shows
  once Play itself has the build for that reader, so nobody is sent to a page
  without an Update button while Play is still reviewing it. On iPhone it
  opens TestFlight (`itms-beta://`), where every tester has the app.
- Pushes go out between 10:00 and 20:00 on the phone's own clock, only to the
  phones still behind (a reader with an updated iPad and an old iPhone hears
  it on the iPhone), and not at all to a reader who has turned every
  notification off, or to a phone not opened in 60 days.
- The words never say what is new, so a build can be announced in its own
  time (group readings are held for Diwali).
- The web app is never asked: it is always the newest.

Nothing is ever blocked until Hawk says so: `required_build` and
`block_after_days` start empty.

## Setting it

One row per platform in `app_releases`, set only through
`POST /api/v1/releases/app-version` with the deployer's Google ID token (as
the release announcement routes).

- **Android latest**: Announce (`announce.yml`) sets it to the build it
  announces, which is on closed testing by then.
- **iOS latest**, **required builds** and **grace periods**: Actions >
  **App versions** (`app-version.yml`) on main. Blank leaves a field as it
  is; `clear` removes a block.
- `APP_UPDATE_REMINDERS=off` on the notifications worker stops the pushes;
  the launch check still answers.

The app asks `GET /api/v1/app/version?platform=&build=` (no sign-in, so a
signed-out phone can be blocked too) on launch and on coming back to the
front, and sends its build with its push token on every launch
(`push_tokens.app_build`).

## Where the code is

- Rules and reminders: `astrospace/notifications/app_updates.py`
  (tests: `tests/test_app_updates.py`)
- Launch check: `astrospace/api/app_version_routes.py`
- Delivery to the phones still behind: `worker.deliver_job` via
  `app_updates.tokens_for_job`
- App: `ui/src/app/core/app-update.service.ts`,
  `ui/src/app/features/mobile/update/`, and
  `ui/android/app/src/main/java/app/asksiddha/mobile/InAppUpdatePlugin.java`

Builds up to 634 (`LAST_SILENT_BUILD`) do not send their build number, so a
push token without one counts as older than any later release. They also
have no update sheet or block, so for them the push is the only reminder.
