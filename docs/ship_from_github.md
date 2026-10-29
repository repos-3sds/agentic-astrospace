# Shipping from GitHub on every merge

Status: canonical. How main reaches Cloud Run, Firebase Hosting, Play
internal testing and TestFlight without the Mac (`.github/workflows/ship.yml`).

## What happens on a merge

1. CI runs on the merge commit as before.
2. When CI is green, **Ship** starts. One run at a time, in merge order; a
   newer merge waits rather than cancelling a deploy halfway.
3. It compares the commit with the last ship that fully succeeded and does only
   what the changed files need:

| Changed | Ships |
| --- | --- |
| `astrospace/`, `main.py`, `requirements.txt`, `Dockerfile`, `ui/` (not `ui/android`, `ui/ios`, `ui/e2e`, specs) | Docker image built in GitHub, pushed to Artifact Registry, `gcloud run deploy --image` on `agentic-astrospace`, health check, then `gcloud run jobs update --image` on `agentic-astrospace-notifications` |
| `firebase.json`, `firebase-public/` | `firebase deploy --only hosting` (asksiddha.app) |
| `ui/` (not `ui/ios`, `ui/e2e`, specs) | Signed AAB, versionCode = commit count, uploaded to **internal** testing with `scripts/play_upload.py`; the AAB is kept as a run artifact for 30 days |
| `ui/` (not `ui/android`, `ui/e2e`, specs) | Signed iOS build, build number = commit count, uploaded to **TestFlight**; see [ship_ios_testflight.md](ship_ios_testflight.md) |

Hosting, the AAB and the iOS build wait for the server, so a build never reaches phones
before the API it calls.

Each upload also drafts "what's new" for testers and emails the team a
preview; testers hear about it only through *Actions › Announce*, on Hawk's
word. See [release_announcements.md](release_announcements.md).

Only the image moves on Cloud Run. Env vars, secrets, scaling and the service
account stay exactly as set by hand, because `deploy --image` and
`jobs update --image` change nothing else.

## What it never does

- **Apply a migration.** A range that adds a file under `supabase/migrations/`
  stops before anything deploys, with the file named in the run summary. Apply
  it (Mac: `supabase db push`, or the SQL Editor), then
  *Actions › Ship › Run workflow* on main with **migrations applied** ticked.
- **Touch production on Play.** `play_upload.py` accepts only internal and
  alpha, and this workflow passes internal. The service account has no
  production rights either. Promoting to closed testing stays a separate step:
  `python3 scripts/play_upload.py --version-code N --track alpha`.
- **Hold a Google key.** GitHub signs in through Workload Identity Federation,
  limited to the main branch of this repository, as `github-deployer` (deploys)
  and `play-publisher` (Play). The only secrets in GitHub are the existing
  Android upload key, its `keystore.properties`, and `google-services.json`.
- **Ship an older commit over a newer one.** If CI for an older commit finishes
  late, that run sees it is no longer the tip of main and skips; the newer run
  already includes it.

If the Mac already uploaded the same commit, the upload step says *Skipped*
and succeeds.

## One-time setup

From the Mac, in the repo folder, signed in to `gcloud` as the owner and to
`gh` as repos-3sds:

```bash
bash scripts/ci/setup_github_ship.sh
```

It creates the Workload Identity pool and provider, the `github-deployer`
service account with run.developer, artifactregistry.writer,
firebasehosting.admin and serviceUsageConsumer, lets it act as the API's and
the job's runtime account, lets GitHub act as `play-publisher`, sets the
`GCP_WIF_PROVIDER` repository variable, and copies the three Android files
into GitHub secrets without printing them. It is safe to run again. It never
creates an upload key: a missing `upload-key.jks` stops it.

Then, once the workflow is on main, run *Actions › Ship › Run workflow* with
**ship everything** ticked to prove every path end to end.

## Where the signing secrets live

The Android upload key and the iOS distribution certificate sit in the
`production` environment, which only `main` may deploy from (sweep
2026-10-29 S-3). The Android and iOS jobs ask for `production` on main and for
`dry-run`, which holds nothing, on a pull request. Before this they were
repository secrets, which any branch that edited a workflow could read.

GitHub never shows a secret's value, so moving them is a Mac step, run once
after the PR that added `environment:` is merged:

    bash scripts/ci/move_signing_secrets.sh ~/AuthKey_KEYID.p8 <issuer-id>

It creates the environment with a main-only branch rule, sets the Android
secrets again from the Mac's own files (the same upload key), makes one new
GitHub-only Apple Distribution certificate for the iOS ones, and only then
deletes the repository-level copies. Without the `.p8`, pass `--android-only`
first; the iOS secrets keep working from repository level until it is run in
full. Until the script runs, the jobs read the repository secrets as before.

A merge that adds a migration also stops the app jobs, not just the server:
they need the plan to have succeeded, so a new build never reaches phones
ahead of the database it needs.

## Manual runs

*Actions › Ship › Run workflow* on main skips the CI gate. Use it after
applying a migration, to retry a failed ship, or with **ship everything** to
redeploy all three regardless of what changed.

## When it fails

GitHub emails the person who merged. The run summary says which part stopped.
The next successful run carries everything since the last good ship, so
nothing is lost by fixing forward. Roll the API back from Cloud Run's
Revisions tab as before.
