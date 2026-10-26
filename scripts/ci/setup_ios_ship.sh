#!/usr/bin/env bash
# One-time setup for the iOS half of .github/workflows/ship.yml
# (docs/ship_ios_testflight.md).
#
# Run on the Mac, from the repo folder, signed in to gh as repos-3sds, after
# Hawk has made an App Store Connect API key (Users and Access > Integrations >
# Team Keys, role Admin) and moved the downloaded AuthKey_XXXX.p8 into the home
# folder. It prints no secret: the key, the new certificate and its password go
# from files straight into `gh secret set`, and the local copies are removed.
#
#   bash scripts/ci/setup_ios_ship.sh ~/AuthKey_ABC123XYZ.p8 <issuer-id>
#
# It creates one new Apple Distribution certificate, used only by GitHub. The
# Mac's own Xcode signing is untouched, and so is every existing certificate.
# Running it again makes another certificate; Apple allows only a few, so run
# it again only if the first one was revoked or the secrets were lost.
set -euo pipefail

REPO=repos-3sds/agentic-astrospace
P8=${1:?usage: setup_ios_ship.sh /path/to/AuthKey_KEYID.p8 ISSUER_ID}
ISSUER=${2:?usage: setup_ios_ship.sh /path/to/AuthKey_KEYID.p8 ISSUER_ID}

cd "$(git rev-parse --show-toplevel)"
[ -f "$P8" ] || { echo "No file at $P8. Move the .p8 out of Downloads into your home folder first."; exit 1; }
KEY_ID=$(basename "$P8" | sed -n 's/^AuthKey_\([A-Z0-9]*\)\.p8$/\1/p')
[ -n "$KEY_ID" ] || { echo "Expected a file named AuthKey_<KEYID>.p8 as Apple names it."; exit 1; }

export ASC_KEY_ID=$KEY_ID ASC_ISSUER_ID=$ISSUER ASC_KEY_FILE=$P8

echo "== The key works"
python3 scripts/asc.py check

WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT
ASC_P12_PASSWORD=$(openssl rand -hex 24)
export ASC_P12_PASSWORD

echo "== New Apple Distribution certificate for GitHub (the Mac's signing is untouched)"
python3 scripts/asc.py create-cert --out-dir "$WORK/cert"

echo "== The certificate can get an App Store profile"
python3 scripts/asc.py profile --serial "$(openssl x509 -in "$WORK/cert/distribution.pem" -noout -serial)" \
  --out "$WORK/check.mobileprovision" | sed -n 's/^name=/profile: /p'

echo "== GitHub secrets (values are not shown)"
gh secret set ASC_KEY_ID -R "$REPO" --body "$KEY_ID"
gh secret set ASC_ISSUER_ID -R "$REPO" --body "$ISSUER"
base64 < "$P8" | tr -d '\n' | gh secret set ASC_KEY_P8_B64 -R "$REPO"
base64 < "$WORK/cert/distribution.p12" | tr -d '\n' | gh secret set IOS_DIST_P12_B64 -R "$REPO"
printf %s "$ASC_P12_PASSWORD" | gh secret set IOS_DIST_P12_PASSWORD -R "$REPO"
gh secret list -R "$REPO"

echo
echo "Done. Keep $P8 somewhere safe (Apple lets you download it only once), or delete it:"
echo "GitHub now holds the only copy the workflow needs."
echo "Next: Actions > Ship > Run workflow on main with 'ship everything' ticked."
