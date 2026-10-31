"""Give one TestFlight build to an external group and send it to Beta App Review.

Ship (scripts/asc.py) uploads every merge to TestFlight and stops there: the
internal group gets it, and nothing reaches the external "Friends and family"
group without a person's word. This is that person's word made into a button:
Actions › TestFlight external › Run workflow, with the build number Hawk named
(.github/workflows/testflight-external.yml). It is never run by a merge.

    python3 scripts/testflight_external.py --build 645
    python3 scripts/testflight_external.py --build 645 --what-to-test "..."

It waits for Apple to finish processing the build, sets "What to Test" if the
build has none, adds the build to the group, and submits it for Beta App
Review unless a submission already exists. It never touches App Store
versions, App Review or a release. Same key as asc.py ($ASC_KEY_ID,
$ASC_ISSUER_ID, $ASC_KEY_FILE or $ASC_KEY_P8), never printed.
"""
from __future__ import annotations

import argparse
import importlib.util
import sys
import time
from pathlib import Path

_spec = importlib.util.spec_from_file_location("asc", Path(__file__).resolve().parent / "asc.py")
asc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(asc)

FRIENDS_AND_FAMILY = "5df5a345-258e-429c-94ab-b2391b4b41ef"
DEFAULT_WHAT_TO_TEST = (
    "Try the newest Siddha. Open Today and tell us if anything looks wrong, "
    "is hard to read or gives a reading that feels off."
)


def find_build(token: str, number: int) -> dict | None:
    data = asc._get("/builds", token, **{"filter[app]": asc.APP_ID, "filter[version]": str(number),
                                         "limit": "10"})
    for build in data.get("data", []):
        if str(build["attributes"].get("version")) == str(number):
            return build
    return None


def wait_until_valid(token: str, number: int, timeout_s: int, poll_s: int = 60,
                     sleep=time.sleep) -> dict:
    """Apple shows a build some minutes after upload and processes it for a few
    more. Only a VALID build can go to a group or to review."""
    waited = 0
    while True:
        build = find_build(token, number)
        state = build["attributes"].get("processingState") if build else None
        if state == "VALID":
            if build["attributes"].get("expired"):
                raise asc.AscError(f"build {number} has expired")
            return build
        if state in ("FAILED", "INVALID"):
            raise asc.AscError(f"Apple marked build {number} {state}")
        if waited >= timeout_s:
            raise asc.AscError(f"build {number} is {state or 'not in App Store Connect'} "
                               f"after {waited // 60} min")
        print(f"build {number}: {state or 'not visible yet'}, waiting")
        sleep(poll_s)
        waited += poll_s


def ensure_what_to_test(token: str, build_id: str, text: str) -> str:
    locs = asc._get(f"/builds/{build_id}/betaBuildLocalizations", token).get("data", [])
    for loc in locs:
        if (loc["attributes"].get("whatsNew") or "").strip():
            return "kept"
    if locs:
        asc._request("PATCH", f"/betaBuildLocalizations/{locs[0]['id']}", token, {"data": {
            "type": "betaBuildLocalizations", "id": locs[0]["id"],
            "attributes": {"whatsNew": text}}})
        return "set"
    asc._request("POST", "/betaBuildLocalizations", token, {"data": {
        "type": "betaBuildLocalizations",
        "attributes": {"locale": "en-US", "whatsNew": text},
        "relationships": {"build": {"data": {"type": "builds", "id": build_id}}}}})
    return "set"


def add_to_group(token: str, group_id: str, build_id: str) -> None:
    # Adding a build the group already has is a no-op on Apple's side.
    asc._request("POST", f"/betaGroups/{group_id}/relationships/builds", token,
                 {"data": [{"type": "builds", "id": build_id}]})


def submit_for_beta_review(token: str, build_id: str) -> str:
    existing = asc._get(f"/builds/{build_id}/betaAppReviewSubmission", token).get("data")
    if existing:
        return existing["attributes"].get("betaReviewState") or "SUBMITTED"
    data = asc._request("POST", "/betaAppReviewSubmissions", token, {"data": {
        "type": "betaAppReviewSubmissions",
        "relationships": {"build": {"data": {"type": "builds", "id": build_id}}}}})["data"]
    return data["attributes"].get("betaReviewState") or "WAITING_FOR_REVIEW"


def external_state(token: str, build_id: str) -> str:
    detail = asc._get(f"/builds/{build_id}/buildBetaDetail", token).get("data") or {}
    return detail.get("attributes", {}).get("externalBuildState") or "unknown"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--build", required=True, type=int, help="the build number, e.g. 645")
    parser.add_argument("--group", default=FRIENDS_AND_FAMILY, help="beta group id")
    parser.add_argument("--what-to-test", default="", help="used only if the build has none")
    parser.add_argument("--wait-minutes", type=int, default=45)
    args = parser.parse_args(argv)

    try:
        token = asc.token_from_env()
        build = wait_until_valid(token, args.build, args.wait_minutes * 60)
        # Tokens live 20 minutes; the wait may have used most of one.
        token = asc.token_from_env()
        build_id = build["id"]
        print(f"build {args.build}: VALID")
        print(f"what to test: {ensure_what_to_test(token, build_id, args.what_to_test.strip() or DEFAULT_WHAT_TO_TEST)}")
        add_to_group(token, args.group, build_id)
        print(f"added to group {args.group}")
        print(f"beta review: {submit_for_beta_review(token, build_id)}")
        print(f"external state: {external_state(token, build_id)}")
    except asc.AscError as exc:
        print(f"testflight_external: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
