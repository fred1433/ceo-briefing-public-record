#!/usr/bin/env python3
"""Re-download every source and check that every quotation is still in it, word for word.

This is the part that makes the briefing checkable by someone who does not trust it.
It needs the network, so it is not in the required build: it runs on demand and on a
weekly schedule. A quotation that no longer resolves is a defect, whether the document
moved or the quotation was wrong in the first place.

    python3 tools/verify_sources.py data/snapshots/2026-09-15.json
"""

from __future__ import annotations

import html
import json
import re
import os
import sys
import time
import urllib.request

# The SEC asks every automated reader to identify itself with a name and a way to
# reach it, and refuses the request otherwise. Nothing is hard coded here, so the
# repository carries no mailbox: set it before running.
#
#     export SEC_USER_AGENT="Your Company you@example.com"
USER_AGENT = os.environ.get("SEC_USER_AGENT", "")
SEPARATOR = " [...] "


def fetch(url: str, tries: int = 4) -> str:
    last = None
    for attempt in range(tries):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(request, timeout=60) as response:
                return response.read().decode("utf-8", "ignore")
        except Exception as exc:  # noqa: BLE001 - the point is to report, not to classify
            last = exc
            time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"{url}: {last}")


def to_text(raw: str) -> str:
    text = re.sub(r"(?is)<(script|style).*?</\1>", " ", raw)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = html.unescape(text)
    for a, b in [("’", "'"), ("‘", "'"), ("“", '"'), ("”", '"'),
                 ("–", "-"), ("—", "-"), (" ", " ")]:
        text = text.replace(a, b)
    return re.sub(r"\s+", " ", text).strip()


def normalise(s: str) -> str:
    for a, b in [("’", "'"), ("‘", "'"), ("“", '"'), ("”", '"'),
                 ("–", "-"), ("—", "-"), (" ", " ")]:
        s = s.replace(a, b)
    return re.sub(r"\s+", " ", s).strip()


def main(path: str) -> int:
    if not USER_AGENT:
        print("set SEC_USER_AGENT to a name and a contact, the SEC refuses anonymous readers",
              file=sys.stderr)
        return 2
    snapshot = json.load(open(path, encoding="utf-8"))
    documents = {e["id"]: e for e in snapshot["evidence"]}
    cache: dict[str, str] = {}
    failures = 0
    checked = 0

    for observation in snapshot["observations"]:
        document = documents[observation["evidence"]]
        url = document["url"]
        if url not in cache:
            cache[url] = to_text(fetch(url))
            time.sleep(0.4)
        body = cache[url]
        for passage in observation["quote"].split(SEPARATOR):
            checked += 1
            if normalise(passage) not in body:
                failures += 1
                print(f"MISSING  {observation['id']}  {url}\n         {passage[:110]}")
    print(f"{checked} passages checked in {len(cache)} documents, {failures} not found")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else "data/snapshots/2026-09-15.json"))
