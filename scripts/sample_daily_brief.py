"""Print one agent-written daily brief for a birth chart, without the app.

    python scripts/sample_daily_brief.py --name "Reader" --birth 1991-08-14T06:12 \
        --city Vijayawada --date 2026-10-16 --tone gentle --mode balanced

Uses AI_PROVIDER / GEMINI_API_KEY / GEMINI_MODEL from the environment (or
.env), exactly as the service does. --signals-only prints what the model
would be given and makes no model call. Nothing is stored.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from astrospace.agents.daily_brief_agent import (  # noqa: E402
    DailyBriefAgent, brief_input, coverage_gaps, listen_seconds, spoken_words,
)
from astrospace.context import daily_guidance  # noqa: E402
from astrospace.core.vedic import VedicChart  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--name", required=True)
    parser.add_argument("--birth", required=True, help="local birth time, YYYY-MM-DDTHH:MM")
    parser.add_argument("--city", required=True)
    parser.add_argument("--nation", default="IN")
    parser.add_argument("--relation", default="self")
    parser.add_argument("--date", help="the day, YYYY-MM-DD (default today)")
    parser.add_argument("--timezone", default="Asia/Kolkata")
    parser.add_argument("--tone", choices=["gentle", "direct"], default="gentle")
    parser.add_argument("--mode", choices=["guided", "balanced", "practitioner"], default="balanced")
    parser.add_argument("--signals-only", action="store_true", help="print the model's input, call nothing")
    args = parser.parse_args()

    born = datetime.fromisoformat(args.birth)
    chart = VedicChart(args.name, born.year, born.month, born.day, born.hour, born.minute,
                       args.city, args.nation)
    zone = ZoneInfo(args.timezone)
    day = datetime.fromisoformat(args.date).date() if args.date else datetime.now(zone).date()
    payload = daily_guidance(chart, relation=args.relation,
                             as_of=datetime(day.year, day.month, day.day, 12, 0, tzinfo=zone))
    first_name = args.name.split()[0]
    label = f"{day:%A}, {day.day} {day:%B}"

    if args.signals_only:
        print(json.dumps(brief_input(payload, first_name, label), indent=2, ensure_ascii=False, default=str))
        return 0

    agent = DailyBriefAgent()
    started = time.monotonic()
    brief = agent.write(payload, first_name=first_name, date_label=label,
                        tone=args.tone, mode=args.mode)
    elapsed = time.monotonic() - started
    if brief is None:
        print("No safe brief was written; the app would keep the templated brief.")
        return 1
    words = spoken_words(brief)
    print(json.dumps(brief.model_dump(), indent=2, ensure_ascii=False))
    usage = agent.usage_totals()
    print(f"\nspoken words: {words}  (~{listen_seconds(words)} s at 0.9x)")
    print(f"coverage gaps: {coverage_gaps(brief, payload, first_name) or 'none'}")
    print(f"model: {usage['model']}  calls: {usage['calls']}  "
          f"tokens in/out: {usage['input_tokens']}/{usage['output_tokens']}  time: {elapsed:.1f} s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
