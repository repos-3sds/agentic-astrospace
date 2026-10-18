"""Every markdown file says what it is in its first three lines (CLAUDE.md,
"Docs state their own status"). Files that predate the check are listed in
docs/doc_status_baseline.txt; anything new must carry a status, and the
baseline only shrinks.

    python scripts/check_doc_status.py            # fail on a new file without one
    python scripts/check_doc_status.py --update   # rewrite the baseline
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASELINE = ROOT / "docs" / "doc_status_baseline.txt"
STATUS = re.compile(r"canonical|source of truth|point-in-time|superseded", re.IGNORECASE)


def tracked_markdown() -> list[str]:
    out = subprocess.run(["git", "ls-files", "*.md"], cwd=ROOT, capture_output=True, text=True, check=True)
    return sorted(line for line in out.stdout.splitlines() if line and not line.startswith("ui/node_modules/"))


def missing_status(paths: list[str]) -> list[str]:
    missing = []
    for path in paths:
        try:
            head = "\n".join((ROOT / path).read_text(encoding="utf-8", errors="replace").splitlines()[:3])
        except OSError:
            continue
        if not STATUS.search(head):
            missing.append(path)
    return missing


def main() -> int:
    missing = missing_status(tracked_markdown())
    if "--update" in sys.argv:
        header = "# Point-in-time list: markdown files that predated scripts/check_doc_status.py without a status line. It only shrinks."
        BASELINE.write_text("\n".join([header, *missing]) + "\n", encoding="utf-8")
        print(f"baseline: {len(missing)} files")
        return 0
    known = set(BASELINE.read_text(encoding="utf-8").splitlines()) if BASELINE.exists() else set()
    new = [path for path in missing if path not in known]
    for path in new:
        print(f"{path}: no status (canonical, source of truth, point-in-time or superseded) in its first three lines")
    return 1 if new else 0


if __name__ == "__main__":
    sys.exit(main())
