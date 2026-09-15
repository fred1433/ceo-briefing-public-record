#!/usr/bin/env python3
"""Write data/run.json: what was run, on what, and what came out.

A briefing that cannot say how it was produced is asking to be taken on trust.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from briefing.cli import paths, run  # noqa: E402


def digest(path: str) -> str:
    return hashlib.sha256(open(path, "rb").read()).hexdigest()[:16]


def main() -> int:
    verification = sys.argv[1] if len(sys.argv) > 1 else "not run in this pass"
    commit = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True
    ).stdout.strip()

    briefings = []
    for date, previous in [("2026-08-31", None), ("2026-09-15", "2026-08-31")]:
        p = paths(date)
        out = run(date, previous, write=False)
        command = f"python3 -m briefing.cli build --date {date}"
        if previous:
            command += f" --previous {previous}"
        briefings.append(
            {
                "date": date,
                "previous": previous,
                "command": command,
                "inputs": {
                    "snapshot": {"path": os.path.relpath(p["snapshot"], ROOT), "sha256_16": digest(p["snapshot"])},
                    "editorial": {"path": os.path.relpath(p["editorial"], ROOT), "sha256_16": digest(p["editorial"])},
                },
                "outputs": {
                    "json": {"path": os.path.relpath(p["json"], ROOT), "sha256_16": digest(p["json"])},
                    "markdown": {"path": os.path.relpath(p["md"], ROOT), "sha256_16": digest(p["md"])},
                },
                "counts": out["counts"],
            }
        )

    trace = {
        "recorded": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "commit": commit,
        "python": sys.version.split()[0],
        "model_calls": 0,
        "editorial_layer": "pre-computed output, written by hand at build time, committed in data/editorial/",
        "briefings": briefings,
        "source_verification": verification,
        "how_to_reproduce": [
            "python3 -m briefing.cli build  --date 2026-08-31",
            "python3 -m briefing.cli build  --date 2026-09-15 --previous 2026-08-31",
            "python3 -m briefing.cli verify --date 2026-09-15 --previous 2026-08-31",
            "python3 -m pytest tests -q",
            'SEC_USER_AGENT="Your Company you@example.com" python3 tools/verify_sources.py data/snapshots/2026-09-15.json',
        ],
    }
    with open(os.path.join(ROOT, "data", "run.json"), "w", encoding="utf-8") as fh:
        json.dump(trace, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    print("data/run.json written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
