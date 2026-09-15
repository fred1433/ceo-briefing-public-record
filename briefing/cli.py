"""Build a briefing from committed snapshots. No network, no model, no surprise."""

from __future__ import annotations

import argparse
import json
import os
import sys

from .model import Snapshot
from .render import build, to_markdown

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")


def paths(date: str) -> dict[str, str]:
    return {
        "snapshot": os.path.join(DATA, "snapshots", f"{date}.json"),
        "editorial": os.path.join(DATA, "editorial", f"{date}.json"),
        "json": os.path.join(DATA, "briefings", f"{date}.json"),
        "md": os.path.join(DATA, "briefings", f"{date}.md"),
    }


def run(date: str, previous: str | None, write: bool) -> dict:
    p = paths(date)
    current = Snapshot.load(p["snapshot"])
    prev = Snapshot.load(paths(previous)["snapshot"]) if previous else None
    editorial = json.load(open(p["editorial"], encoding="utf-8"))
    out = build(current, prev, editorial)
    if write:
        with open(p["json"], "w", encoding="utf-8") as fh:
            json.dump(out, fh, ensure_ascii=False, indent=1)
            fh.write("\n")
        with open(p["md"], "w", encoding="utf-8") as fh:
            fh.write(to_markdown(out))
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="briefing")
    ap.add_argument("command", choices=["build", "verify"])
    ap.add_argument("--date", required=True)
    ap.add_argument("--previous", default=None)
    args = ap.parse_args(argv)

    if args.command == "build":
        out = run(args.date, args.previous, write=True)
        print(f"{args.date}: {out['counts']['items']} items, "
              f"{out['counts']['changes']} changes, {out['counts']['evidence']} documents")
        return 0

    out = run(args.date, args.previous, write=False)
    p = paths(args.date)
    committed = json.load(open(p["json"], encoding="utf-8"))
    if committed != out:
        print(f"{args.date}: committed briefing differs from a fresh build", file=sys.stderr)
        return 1
    if open(p["md"], encoding="utf-8").read() != to_markdown(out):
        print(f"{args.date}: committed markdown differs from a fresh build", file=sys.stderr)
        return 1
    print(f"{args.date}: reproducible")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
