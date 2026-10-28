"""List the merged pull requests between two app builds, as JSON for
/api/v1/releases/draft (docs/release_announcements.md).

A build's versionCode is the commit count of main when it was built
(ship.yml), so the commit behind a versionCode is the first-parent commit on
main whose count matches. Each first-parent commit is one merged pull request
(squash merges), listed with the files it touched so the server can leave
out changes testers never see.

    python3 scripts/release_changes.py --since 574            # 574..HEAD
    python3 scripts/release_changes.py --since 574 --to-version 580

Standard library and git only.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys

# When testers hold no build yet, or the old one is not on this history, look
# back this far rather than at the whole of main.
FALLBACK_COMMITS = 15


def git(*args: str) -> str:
    return subprocess.run(["git", *args], check=True, capture_output=True, text=True).stdout


def commit_for_version(version_code: int, head: str = "HEAD") -> str | None:
    """The first-parent commit of `head` whose ancestor count is version_code."""
    for sha in git("rev-list", "--first-parent", head).split():
        count = int(git("rev-list", "--count", sha).strip())
        if count == version_code:
            return sha
        if count < version_code:
            return None
    return None


def changes(since: str | None, to: str = "HEAD") -> list[dict]:
    if since:
        range_args = [f"{since}..{to}"]
    else:
        range_args = [f"--max-count={FALLBACK_COMMITS}", to]
    out = []
    for sha in git("rev-list", "--first-parent", *range_args).split():
        title = git("log", "-1", "--format=%s", sha).strip()
        files = [f for f in git("diff-tree", "--no-commit-id", "--name-only", "-r", "-m",
                                "--first-parent", sha).split("\n") if f]
        out.append({"title": title, "files": files})
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--since", type=int, default=0,
                        help="versionCode testers have now (0: none)")
    parser.add_argument("--to", default="HEAD", help="commit of the new build (default HEAD)")
    parser.add_argument("--to-version", type=int, help="versionCode of the new build, instead of --to")
    args = parser.parse_args(argv)
    if args.to_version:
        args.to = commit_for_version(args.to_version) or "HEAD"
    base = commit_for_version(args.since, args.to) if args.since > 0 else None
    if args.since > 0 and base is None:
        print(f"release_changes: no commit on main for versionCode {args.since}; "
              f"using the last {FALLBACK_COMMITS}", file=sys.stderr)
    json.dump(changes(base, args.to), sys.stdout, indent=1)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
