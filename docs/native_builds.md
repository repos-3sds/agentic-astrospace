# Native Builds (Capacitor)

Covers Epic M11-US01. The Angular application is packaged for iOS and Android
with Capacitor; there is no second codebase and no product logic in the native
projects.

## What is committed

`ui/android` and `ui/ios` are committed because they hold real configuration —
bundle identifier, permissions, icons, entitlements — that must be reviewable.
Their build output and the synced web bundle are not committed:
`npx cap sync` regenerates those from `frontend/dist` on every build, so
tracking them produces nothing but merge conflicts.

## Commands

```bash
cd ui

npm run build:native      # ng build --configuration production && npx cap sync
npm run open:ios          # opens Xcode
npm run open:android      # opens Android Studio
```

Use `build:native` rather than `npx cap sync` on its own. `sync` copies
whatever already sits in `frontend/dist`, so running it after editing source
but before rebuilding ships a stale bundle into the app — with no error.

## API origin

This is the one difference between web and native, and it fails silently if
missed.

On the web, FastAPI serves the SPA, so the API shares the page's origin and a
relative path (`/api/v1/...`) is correct — it follows the deployment to
whatever host it lands on.

A Capacitor WebView serves the bundle from `https://localhost`. A relative path
there resolves against the *bundle*, not the server, so every request 404s
inside the app with nothing in the network log to explain it.

`ui/src/app/core/api-origin.ts` resolves this:

| Platform | Origin |
| --- | --- |
| Web (`ng serve`, deployed SPA) | relative, unchanged |
| Native | `environment.nativeApiOrigin`, absolute |

Set `nativeApiOrigin` in `ui/src/environments/environment.prod.ts` before
building for a device. It is deliberately empty by default: an empty value
throws immediately with an explanatory message, whereas a wrong one surfaces
later as an opaque CORS failure.

A simulator can reach the host on `http://localhost:8000`. A physical device
cannot, and needs the machine's LAN address or the deployed URL.

## CORS

Because the WebView is a genuine cross-origin caller, the API must allow its
origin. `main.py` includes `https://localhost` and `capacitor://localhost` in
the defaults. Any deployment that overrides `ALLOWED_ORIGINS` must keep them,
or the native apps will fail on device only.

## Host requirements

Building for a simulator needs Xcode's iOS **platform** component, which is a
separate download from the SDK stubs. Without it every destination resolves to
the "Any iOS Device" placeholder and xcodebuild reports:

```text
IDERunDestination: Supported platforms for the buildables in the current scheme is empty.
error: iOS 26.5 is not installed. Please download and install the platform from
       Xcode > Settings > Components.
```

Install it from **Xcode > Settings > Components**, or:

```bash
xcodebuild -downloadPlatform iOS
```

`xcodebuild -showsdks` listing an iOS SDK is not sufficient — the SDK stub and
the platform component are tracked separately, so the SDK can appear installed
while the platform is missing.

Android likewise needs the Android SDK; `npx cap add android` warns
`Unable to infer default Android SDK settings` when it is absent.

## Not yet done

- Add `app.astrospace.mobile://auth/callback` to the Supabase Redirect URLs
  allowlist before testing a real magic link, password recovery, or Google
  return (M11-US02).
- Complete the Android lifecycle matrix beyond launch, keyboard, route Back,
  and callback-intent delivery (M11-US03).
- Push notification registration (M11-US04).
- Splash screen and icon assets are Capacitor defaults so far.
- The native projects are not in CI.

## Verified on iOS

The development bundle has been built, synced, installed, and launched on
iPhone 17 Pro simulators running iOS 26.2 and 26.5. The edge-to-edge WebView,
status/home safe areas, unauthenticated landing bootstrap, and restored-session
handoff into `/m` are verified.

Local real-auth configuration is enabled and its API accepts the native
`https://localhost` origin. Cloud Run revision
`agentic-astrospace-00024-5rf` was deployed with that configuration and serves
100% of traffic; the production native preflight now returns HTTP 200.

The iOS and Android projects register
`app.astrospace.mobile://auth/callback`. OAuth launches in the system browser,
PKCE callbacks are exchanged for a Supabase session, magic-link token
callbacks are accepted, and password recovery lands on `/m/reset-password`.
Supabase must allowlist the callback URL before those hosted flows can return
to the app.

The production Android bundle has also been built, installed, and launched on
the API 36.1 `Medium_Phone` emulator. Landing rendering, keyboard resize, route
Back, and callback-intent delivery are verified. Build Android with Android
Studio's bundled JDK 21; the host's Java 25 is newer than this Gradle/Groovy
toolchain supports.

No controlled test inbox or test credentials are configured in the workspace,
so email confirmation and password-reset delivery have not been exercised
against a real account. Do not create disposable Supabase users without one.
