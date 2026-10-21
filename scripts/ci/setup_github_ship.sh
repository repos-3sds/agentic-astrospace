#!/usr/bin/env bash
# One-time setup for .github/workflows/ship.yml (docs/ship_from_github.md).
#
# Run on the Mac, from the repo folder, signed in to gcloud as the project
# owner and to gh as repos-3sds. Safe to run twice: everything that exists is
# left as it is. It prints no secret: the keystore, its passwords and
# google-services.json go from their files straight into `gh secret set`.
#
#   bash scripts/ci/setup_github_ship.sh            # Google side + GitHub secrets
#   bash scripts/ci/setup_github_ship.sh --no-secrets
set -euo pipefail

PROJECT=gen-lang-client-0058562386
REGION=asia-south1
REPO=repos-3sds/agentic-astrospace
POOL=github
PROVIDER=agentic-astrospace
DEPLOYER=github-deployer@$PROJECT.iam.gserviceaccount.com
PLAY_SA=play-publisher@$PROJECT.iam.gserviceaccount.com
ANDROID_DIR=ui/android

cd "$(git rev-parse --show-toplevel)"
PNUM=$(gcloud projects describe "$PROJECT" --format='value(projectNumber)')
POOL_ID=projects/$PNUM/locations/global/workloadIdentityPools/$POOL
REPO_MEMBER="principalSet://iam.googleapis.com/$POOL_ID/attribute.repository/$REPO"

echo "== APIs"
gcloud services enable iamcredentials.googleapis.com sts.googleapis.com \
  artifactregistry.googleapis.com firebasehosting.googleapis.com --project "$PROJECT"

echo "== Workload Identity pool and GitHub provider (main branch of $REPO only)"
gcloud iam workload-identity-pools describe "$POOL" --project "$PROJECT" --location global >/dev/null 2>&1 ||
  gcloud iam workload-identity-pools create "$POOL" --project "$PROJECT" --location global \
    --display-name "GitHub Actions"
gcloud iam workload-identity-pools providers describe "$PROVIDER" --project "$PROJECT" --location global \
  --workload-identity-pool "$POOL" >/dev/null 2>&1 ||
  gcloud iam workload-identity-pools providers create-oidc "$PROVIDER" --project "$PROJECT" --location global \
    --workload-identity-pool "$POOL" --display-name "agentic-astrospace main" \
    --issuer-uri "https://token.actions.githubusercontent.com" \
    --attribute-mapping "google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.ref=assertion.ref" \
    --attribute-condition "assertion.repository=='$REPO' && assertion.ref=='refs/heads/main'"

echo "== Deployer service account"
gcloud iam service-accounts describe "$DEPLOYER" --project "$PROJECT" >/dev/null 2>&1 ||
  gcloud iam service-accounts create github-deployer --project "$PROJECT" \
    --display-name "GitHub Actions: deploy API, worker image and Hosting"
# Image pushes, Cloud Run image updates, Hosting deploys. No secret access,
# no IAM admin: it cannot read or change the services' secrets.
for role in roles/run.developer roles/artifactregistry.writer roles/firebasehosting.admin \
            roles/serviceusage.serviceUsageConsumer; do
  gcloud projects add-iam-policy-binding "$PROJECT" --member "serviceAccount:$DEPLOYER" \
    --role "$role" --condition None --quiet >/dev/null
done

# Deploying a revision "acts as" the identity it runs under.
DEFAULT_SA=$PNUM-compute@developer.gserviceaccount.com
API_SA=$(gcloud run services describe agentic-astrospace --region "$REGION" --project "$PROJECT" \
  --format='value(spec.template.spec.serviceAccountName)')
JOB_SA=$(gcloud run jobs describe agentic-astrospace-notifications --region "$REGION" --project "$PROJECT" \
  --format='value(spec.template.spec.template.spec.serviceAccountName)')
for sa in $(printf '%s\n' "${API_SA:-$DEFAULT_SA}" "${JOB_SA:-$DEFAULT_SA}" | sort -u); do
  gcloud iam service-accounts add-iam-policy-binding "$sa" --project "$PROJECT" \
    --member "serviceAccount:$DEPLOYER" --role roles/iam.serviceAccountUser --quiet >/dev/null
done

echo "== GitHub Actions may act as the deployer and as play-publisher (no keys)"
for sa in "$DEPLOYER" "$PLAY_SA"; do
  gcloud iam service-accounts add-iam-policy-binding "$sa" --project "$PROJECT" \
    --member "$REPO_MEMBER" --role roles/iam.workloadIdentityUser --quiet >/dev/null
done

echo "== Image repository"
gcloud artifacts repositories describe cloud-run-source-deploy --location "$REGION" --project "$PROJECT" >/dev/null 2>&1 ||
  gcloud artifacts repositories create cloud-run-source-deploy --repository-format docker \
    --location "$REGION" --project "$PROJECT" --description "Cloud Run images"

echo "== GitHub variable GCP_WIF_PROVIDER"
gh variable set GCP_WIF_PROVIDER -R "$REPO" --body "$POOL_ID/providers/$PROVIDER"

if [ "${1:-}" = "--no-secrets" ]; then
  echo "Skipped the GitHub secrets (--no-secrets)."; exit 0
fi

echo "== GitHub secrets from the Mac's existing files (values are not shown)"
for f in "$ANDROID_DIR/upload-key.jks" "$ANDROID_DIR/keystore.properties" "$ANDROID_DIR/app/google-services.json"; do
  [ -f "$f" ] || { echo "Missing $f; nothing set. Never create a new upload key."; exit 1; }
done
base64 < "$ANDROID_DIR/upload-key.jks" | tr -d '\n' | gh secret set ANDROID_UPLOAD_KEYSTORE_B64 -R "$REPO"
gh secret set ANDROID_KEYSTORE_PROPERTIES -R "$REPO" < "$ANDROID_DIR/keystore.properties"
base64 < "$ANDROID_DIR/app/google-services.json" | tr -d '\n' | gh secret set ANDROID_GOOGLE_SERVICES_JSON_B64 -R "$REPO"
gh secret list -R "$REPO"
echo "Done. Next: merge the Ship PR, then Actions > Ship > Run workflow on main with 'ship everything'."
