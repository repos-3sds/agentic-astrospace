# Custom domain: asksiddha.app

Status: canonical. How the public address reaches the Cloud Run service.

The domain is registered at Cloudflare. Cloud Run's own domain mapping isn't offered in
`asia-south1`, so Firebase Hosting (same Google project) sits in front: `firebase.json`
forwards every path to the `agentic-astrospace` service. The web app stays same-origin,
so no CORS change is needed.

## One-time setup

1. `npm i -g firebase-tools && firebase login`, then from the repo root
   `firebase deploy --only hosting`. Redeploy this only when `firebase.json` changes; app
   deploys go to Cloud Run as before.
2. Firebase console › Hosting › Add custom domain › `asksiddha.app`. Add the records it
   shows in Cloudflare DNS with the proxy **off** (grey cloud, "DNS only"), or Firebase
   can't issue the certificate. `.app` is HTTPS-only, so the site works once the
   certificate is issued.
3. Cloud Run, on both the service and the `agentic-astrospace-notifications` job:
   `PUBLIC_BASE_URL=https://asksiddha.app` (email links and the email logo).
4. Supabase › Authentication › URL configuration: Site URL `https://asksiddha.app`, and
   add `https://asksiddha.app/**` to the redirect URLs.

## Limits and what stays on the old address

- Firebase Hosting gives a request to Cloud Run at most 60 seconds. A daily brief that
  hasn't been pre-written can take longer to write on demand; the worker writes them the
  night before, so this only bites a web reader whose brief wasn't cached.
- The native app keeps calling `https://agentic-astrospace-cwuqybpnzq-el.a.run.app`
  (`nativeApiOrigin`, and the Android sign-in callback in `AndroidManifest.xml`). That
  address keeps working, and switching it means a new store build, so it waits until the
  domain has proven itself.
