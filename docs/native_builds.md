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

## Not yet done

- Deep links and native OAuth return (M11-US02).
- Android back-button and lifecycle handling (M11-US03).
- Push notification registration (M11-US04).
- Safe-area, splash screen and icon assets are Capacitor defaults so far.
- The native projects are not in CI.
