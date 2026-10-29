#!/usr/bin/env bash
# Moves the app-signing secrets into a GitHub environment only main can use
# (sweep 2026-10-29 S-3). Run once on the Mac, from the repo folder, signed in
# to gh as repos-3sds, after the Ship PR that adds `environment:` is merged.
#
#   bash scripts/ci/move_signing_secrets.sh ~/AuthKey_KEYID.p8 <issuer-id>
#
# GitHub never shows a secret's value, so they can't be copied across:
# - Android: set again from the Mac's own files (the same upload key; never
#   a new one), as setup_github_ship.sh does.
# - iOS: setup_ios_ship.sh makes one new Apple Distribution certificate for
#   GitHub, which needs the App Store Connect .p8 key, and then revokes the
#   old GitHub one (REPLACE_SERIAL, made 2026-10-26) so the team's certificate
#   count stays the same. Without the .p8, pass --android-only and the iOS
#   secrets stay at repository level for now.
# The repository-level copies are deleted only once the environment holds
# its own. Prints no secret.
set -euo pipefail

REPO=repos-3sds/agentic-astrospace
ENV=production
ANDROID=(ANDROID_UPLOAD_KEYSTORE_B64 ANDROID_KEYSTORE_PROPERTIES ANDROID_GOOGLE_SERVICES_JSON_B64)
# The GitHub-only certificate setup_ios_ship.sh made on 2026-10-26.
REPLACE_SERIAL=${REPLACE_SERIAL:-71215B8541AAA30F2B39143D2F7F0B6D}
IOS=(ASC_KEY_ID ASC_ISSUER_ID ASC_KEY_P8_B64 IOS_DIST_P12_B64 IOS_DIST_P12_PASSWORD)

cd "$(git rev-parse --show-toplevel)"
ANDROID_ONLY=false
if [ "${1:-}" = "--android-only" ]; then ANDROID_ONLY=true; shift; fi

echo "== Environment '$ENV', deployable from main only"
gh api -X PUT "repos/$REPO/environments/$ENV" --input - >/dev/null <<JSON
{"deployment_branch_policy": {"protected_branches": false, "custom_branch_policies": true}}
JSON
if ! gh api "repos/$REPO/environments/$ENV/deployment-branch-policies" --jq '.branch_policies[].name' | grep -qx main; then
  gh api -X POST "repos/$REPO/environments/$ENV/deployment-branch-policies" -f name=main -f type=branch >/dev/null
fi
gh api "repos/$REPO/environments/$ENV/deployment-branch-policies" --jq '"branches allowed: " + ([.branch_policies[].name] | join(", "))'

echo "== Android secrets into '$ENV'"
SECRETS_ENV=$ENV bash scripts/ci/setup_github_ship.sh --secrets-only
MOVED=("${ANDROID[@]}")

if [ "$ANDROID_ONLY" = false ]; then
  echo "== iOS secrets into '$ENV' (one new GitHub-only certificate)"
  SECRETS_ENV=$ENV REPLACE_SERIAL=$REPLACE_SERIAL bash scripts/ci/setup_ios_ship.sh "$@"
  MOVED+=("${IOS[@]}")
fi

echo "== Repository-level copies removed"
HAVE=$(gh secret list -R "$REPO" --env "$ENV" --json name --jq '.[].name')
for name in "${MOVED[@]}"; do
  if grep -qx "$name" <<<"$HAVE"; then
    gh secret delete "$name" -R "$REPO" 2>/dev/null && echo "removed $name" || echo "$name was not at repository level"
  else
    echo "kept $name at repository level: not found in '$ENV'"
  fi
done
echo "Done. Next: Actions > Ship > Run workflow on main with 'ship everything' to prove it."
