"""Thin CLI over store.py: `python -m winnow.cli stats|recent`."""
import argparse
import json

from winnow import store


def main(argv=None):
    parser = argparse.ArgumentParser(prog="winnow")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("stats", help="show aggregate token savings")
    recent_p = sub.add_parser("recent", help="show recent logged requests")
    recent_p.add_argument("-n", "--limit", type=int, default=20)

    args = parser.parse_args(argv)
    if args.command == "stats":
        print(json.dumps(store.aggregate_savings(), indent=2))
    elif args.command == "recent":
        print(json.dumps(store.query_recent(args.limit), indent=2))


if __name__ == "__main__":
    main()
