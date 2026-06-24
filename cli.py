#!/usr/bin/env python3
"""AstroSpace CLI"""
import argparse
import json
from dotenv import load_dotenv

load_dotenv()


def main():
    parser = argparse.ArgumentParser(description="AstroSpace — AI Astrology Engine")
    sub = parser.add_subparsers(dest="cmd")

    def add_birth_args(p):
        p.add_argument("--name", required=True)
        p.add_argument("--year", type=int, required=True)
        p.add_argument("--month", type=int, required=True)
        p.add_argument("--day", type=int, required=True)
        p.add_argument("--hour", type=int, default=12)
        p.add_argument("--minute", type=int, default=0)
        p.add_argument("--city", required=True)
        p.add_argument("--nation", default="US")

    add_birth_args(sub.add_parser("chart", help="Calculate natal chart"))
    add_birth_args(sub.add_parser("reading", help="AI natal chart reading"))
    add_birth_args(sub.add_parser("transits", help="Personal transit reading"))

    hp = sub.add_parser("horoscope", help="Daily/weekly horoscope")
    hp.add_argument("--sign", required=True)
    hp.add_argument("--weekly", action="store_true")

    sub.add_parser("sky", help="Current planetary positions")

    args = parser.parse_args()

    if args.cmd == "chart":
        from astrospace.core.chart import BirthChart
        chart = BirthChart(args.name, args.year, args.month, args.day,
                           args.hour, args.minute, args.city, args.nation)
        print(json.dumps(chart.to_dict(), indent=2))

    elif args.cmd == "reading":
        from astrospace.agents.reading_agent import ReadingAgent
        agent = ReadingAgent()
        print(agent.get_full_reading(
            args.name, args.year, args.month, args.day,
            args.hour, args.minute, args.city, args.nation,
        ))

    elif args.cmd == "horoscope":
        from astrospace.agents.horoscope_agent import HoroscopeAgent
        agent = HoroscopeAgent()
        if args.weekly:
            print(agent.get_weekly_horoscope(args.sign))
        else:
            print(agent.get_daily_horoscope(args.sign))

    elif args.cmd == "sky":
        from astrospace.core.transits import TransitCalculator
        calc = TransitCalculator()
        print(json.dumps(calc.get_current_transits(), indent=2))

    elif args.cmd == "transits":
        from astrospace.agents.transit_agent import TransitAgent
        agent = TransitAgent()
        print(agent.get_transit_reading(
            args.name, args.year, args.month, args.day,
            args.hour, args.minute, args.city, args.nation,
        ))

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
