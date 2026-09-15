"""No line of a briefing without a source, and no source without a quotation.

This runs against the two briefings that are actually published, not against a
fixture: if a line of the real product loses its anchor, the build stops.
"""

import json
import os

import pytest

from briefing.cli import paths, run
from briefing.model import Snapshot
from briefing.render import SourcingError, build

DATES = [("2026-08-31", None), ("2026-09-15", "2026-08-31")]


@pytest.mark.parametrize("date,previous", DATES)
def test_every_fact_carries_a_quoted_public_document(date, previous):
    out = run(date, previous, write=False)
    assert out["items"], "a briefing with no items is a bug, not an empty day"
    for item in out["items"]:
        for step in item["chain"]:
            if step["register"] != "fact":
                continue
            assert step["sources"], f"{item['key']}.{step['field']} has no source"
            quoted = [s for s in step["sources"] if s["quote"]]
            assert quoted, f"{item['key']}.{step['field']} has no quotation"
            for s in step["sources"]:
                assert s["url"].startswith("https://")
                assert s["published"] <= date


@pytest.mark.parametrize("date,previous", DATES)
def test_committed_briefing_matches_a_fresh_build(date, previous):
    from briefing.cli import main

    assert main(["verify", "--date", date] + (["--previous", previous] if previous else [])) == 0


def test_a_fact_without_a_source_is_refused():
    snap = Snapshot.load(paths("2026-09-15")["snapshot"])
    editorial = {
        "headline": "h",
        "scope": "s",
        "items": [
            {
                "key": "obl-10k-fy2026",
                "headline": "unsourced",
                "chain": {"what_happened": {"text": "Something is true.", "sources": []}},
            }
        ],
    }
    with pytest.raises(SourcingError):
        build(snap, None, editorial)


def test_an_unknown_source_id_is_refused():
    snap = Snapshot.load(paths("2026-09-15")["snapshot"])
    editorial = {
        "headline": "h",
        "scope": "s",
        "items": [
            {
                "key": "obl-10k-fy2026",
                "headline": "dangling",
                "chain": {"what_happened": {"text": "Something.", "sources": ["obs-that-does-not-exist"]}},
            }
        ],
    }
    with pytest.raises(SourcingError):
        build(snap, None, editorial)


def test_snapshots_are_internally_consistent():
    for date, _ in DATES:
        snap = Snapshot.load(paths(date)["snapshot"])
        snap.check()
        assert snap.evidence and snap.observations and snap.obligations


def test_no_email_address_is_published():
    """A briefing about a public company names roles, never mailboxes."""
    for date, previous in DATES:
        blob = json.dumps(run(date, previous, write=False))
        assert "@" not in blob
