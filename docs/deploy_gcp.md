# Deploying AstroSpace to Google Cloud Run

Single-container deployment: the Dockerfile builds the Angular SPA and serves
it plus the FastAPI API from one Cloud Run service. AI features are not wired
into the product yet, so no ANTHROPIC_API_KEY is needed in production.

## Architecture

```
Browser ──► Cloud Run (asia-south1)          ──► Supabase (Auth + Postgres)
            FastAPI + Angular SPA (1 container)
            scales to zero; free tier: 2M req/mo
```

- The container filesystem is EPHEMERAL. SQLite is dev-only; production must
  set DATABASE_URL to Supabase Postgres (use the pooler URL, port 6543 —
  Cloud Run instances come and go, the pooler absorbs that).
- `PORT` is injected by Cloud Run; the image honors it.
- Health check: `GET /api/health`.

## One-time setup (user actions)

1. Install the gcloud CLI: https://cloud.google.com/sdk/docs/install
   then `gcloud auth login`.
2. Create a project (console or CLI):
   `gcloud projects create astrospace-prod --set-as-default`
3. Attach a billing account (required even for free-tier usage):
   console → Billing. Usage at launch scale stays inside the free tier.
4. Enable services:
   `gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com`

## Supabase (user actions)

1. In the Supabase dashboard → Project Settings → Database, copy the
   **connection pooler** URI (port 6543, `postgresql://...pooler.supabase.com:6543/postgres`).
2. Authentication → URL Configuration: add the Cloud Run URL (and later the
   custom domain) to **Redirect URLs** and set **Site URL** — magic links and
   OAuth land here.
3. Free-tier note: the project pauses after ~7 days of inactivity; unpause
   from the dashboard.

## Deploy

From the repo root (Cloud Build builds the Dockerfile remotely — no local
Docker needed):

```bash
gcloud run deploy agentic-astrospace \
  --source . \
  --region asia-south1 \
  --allow-unauthenticated \
  --memory 1Gi \
  --set-env-vars "SUPABASE_URL=https://YOUR-PROJECT.supabase.co,SUPABASE_ANON_KEY=YOUR_ANON_KEY"
```

Set the database URL as a secret rather than a plain env var:

```bash
echo -n "postgresql://postgres.YOUR-REF:YOUR_DB_PASSWORD@aws-0-ap-south-1.pooler.supabase.com:6543/postgres" | \
  gcloud secrets create astrospace-database-url --data-file=-
gcloud run services update agentic-astrospace --region asia-south1 \
  --set-secrets "DATABASE_URL=astrospace-database-url:latest"
```

(Grant the Cloud Run service account `roles/secretmanager.secretAccessor` if
prompted.)

## After first deploy

1. Note the service URL (`https://astrospace-....run.app`) and add it to
   Supabase Redirect URLs (step above).
2. Verify: `curl https://.../api/health` → `{"status":"ok"}`; open the URL,
   sign in, load a kundli.
3. Custom domain (optional):
   `gcloud run domain-mappings create --service astrospace --domain app.yourdomain.com --region asia-south1`
   then add the DNS records it prints at your registrar. TLS is automatic.

## Environment variables (production)

| Var | Required | Value |
|---|---|---|
| DATABASE_URL | yes | Supabase pooler URI (secret) |
| SUPABASE_URL | yes | https://YOUR-PROJECT.supabase.co |
| SUPABASE_ANON_KEY | yes | anon public key (safe to expose; it's shipped to browsers anyway) |
| ALLOWED_ORIGINS | no | extra CORS origins, comma-separated (SPA is same-origin; only needed for a split frontend later) |
| GEONAMES_USERNAME | no | only if online geocoding fallback is wanted |
| AI_PROVIDER | yes for Ask | `gemini` for the mobile Ask experience; `anthropic` remains available as a fallback |
| GEMINI_API_KEY | yes when AI_PROVIDER=gemini | Gemini API key for Ask and agentic explanations |
| GEMINI_MODEL | no | Defaults to `gemini-3.5-flash` |
| GEMINI_BACKEND | no | `vertex` runs Gemini on Vertex AI, billed to this Google Cloud project with no API key; unset keeps AI Studio and `GEMINI_API_KEY` |
| GOOGLE_CLOUD_PROJECT | with `GEMINI_BACKEND=vertex` | the project id, e.g. `gen-lang-client-0058562386` |
| GOOGLE_CLOUD_LOCATION | no | Vertex AI location; defaults to `global` |
| ANTHROPIC_API_KEY | yes when AI_PROVIDER=anthropic | Anthropic API key for fallback/provider switch |

## Gemini on Vertex AI

AI Studio bills from prepaid credit, and when it ran out on 2026-10-17 every
AI feature failed at once. Vertex AI serves the same models on the project's
normal bill and signs in as the service account. To switch (once):

```bash
gcloud services enable aiplatform.googleapis.com
SA=$(gcloud run services describe agentic-astrospace --region asia-south1 \
  --format='value(spec.template.spec.serviceAccountName)')
gcloud projects add-iam-policy-binding gen-lang-client-0058562386 \
  --member "serviceAccount:$SA" --role roles/aiplatform.user
# Do the same for the notifications job's service account if it differs.
gcloud run services update agentic-astrospace --region asia-south1 \
  --update-env-vars GEMINI_BACKEND=vertex,GOOGLE_CLOUD_PROJECT=gen-lang-client-0058562386
gcloud run jobs update agentic-astrospace-notifications --region asia-south1 \
  --update-env-vars GEMINI_BACKEND=vertex,GOOGLE_CLOUD_PROJECT=gen-lang-client-0058562386
```

Then ask one question in the app. To roll back, remove `GEMINI_BACKEND`
(`--remove-env-vars GEMINI_BACKEND`); `GEMINI_API_KEY` is still used then.

Every model call writes one JSON line to the `astrospace.ai.usage` logger:
feature, purpose, model, input, output and cached tokens. Searching Logs
Explorer for `"feature":` lists them, and a log-based metric on those lines
gives spend per feature.

## Updating

Re-run the same `gcloud run deploy astrospace --source . --region asia-south1`
— Cloud Run does a zero-downtime revision swap. Roll back from the console
(Revisions tab) or `gcloud run services update-traffic`.

## Cost guardrails

- Scale-to-zero is default; free tier covers ~2M requests/month.
- Set a budget alert: console → Billing → Budgets → e.g. $5 alert.
- `--max-instances 2` caps the worst case:
  `gcloud run services update agentic-astrospace --region asia-south1 --max-instances 2`
