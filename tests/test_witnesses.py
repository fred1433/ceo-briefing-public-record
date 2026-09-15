"""Two witnesses the reader can check without trusting anything we say.

Silence     the same sources, read twice, produce no item and no alert. A system
            that cannot stay quiet cannot be believed when it speaks.
Correction  the Form 10-Q/A of August 6, 2026 states one correction. The briefing
            reports that correction and does not republish the quarter's figures
            as if they were news.
"""

import json
import re

import pytest

from briefing.cli import paths, run
from briefing.diff import diff
from briefing.model import Snapshot


def test_silence_the_same_sources_twice_produce_nothing():
    snap = Snapshot.load(paths("2026-09-15")["snapshot"])
    assert diff(snap, snap) == []


def test_silence_is_reported_as_silence_on_the_page():
    """The August briefing replays the alert rule over its window and says it did not fire."""
    out = run("2026-08-31", None, write=False)
    crosses = out["alert_rule"]["crosses"]
    assert crosses["sources"] == []
    assert "stays silent" in crosses["text"]


def test_the_alert_rule_fires_once_the_event_is_in_the_window():
    out = run("2026-09-15", "2026-08-31", write=False)
    crosses = out["alert_rule"]["crosses"]
    assert crosses["sources"], "the September window contains the event the rule is written for"
    assert "September 8" in crosses["when"]


def test_a_document_and_the_exhibit_it_carries_are_one_event():
    """A press release furnished with the filing it accompanies is not a second event."""
    snap = Snapshot.load(paths("2026-09-15")["snapshot"])
    empty = Snapshot(as_of=snap.as_of, company=snap.company, ticker=snap.ticker, cik=snap.cik)
    appeared = [c for c in diff(empty, snap) if c.kind == "appeared" and len(c.evidence) > 1]
    assert appeared, "the corpus contains filings that carry an exhibit"
    for change in appeared:
        events = {snap.evidence[e].event_id for e in change.evidence}
        assert len(events) == 1


@pytest.mark.parametrize("date,previous", [("2026-08-31", None), ("2026-09-15", "2026-08-31")])
def test_correction_the_amendment_states_one_correction_and_nothing_else(date, previous):
    snap = Snapshot.load(paths(date)["snapshot"])
    facts = [o.fact for o in snap.observations.values() if o.evidence == "10qa-q3-fy2026"]
    assert facts, "the amendment is in the corpus"
    assert all("Series D" in f or "amended" in f for f in facts)

    out = run(date, previous, write=False)
    carried = [c for c in out["carried"] if "Series D" in c["text"]]
    assert carried, "the amendment is reported as a correction"
    assert "republishes none of the quarter's figures" in carried[0]["text"]


@pytest.mark.parametrize("date,previous", [("2026-08-31", None), ("2026-09-15", "2026-08-31")])
def test_no_quarterly_figure_is_republished_as_news(date, previous):
    """Nothing sourced to the amendment or to the quarterly report carries a money figure."""
    out = run(date, previous, write=False)
    for item in out["items"]:
        for step in item["chain"]:
            ids = {s["id"] for s in step["sources"]}
            if not ids & {"10qa-reason", "10qa-subject", "10q-period"}:
                continue
            assert not re.search(r"\$\s?\d", step["text"])


@pytest.mark.parametrize("date,previous", [("2026-08-31", None), ("2026-09-15", "2026-08-31")])
def test_what_is_not_established_is_said_and_not_guessed(date, previous):
    """The fourth register is exercised, not merely available."""
    out = run(date, previous, write=False)
    unknowns = [
        step
        for item in out["items"]
        for step in item["chain"]
        if step["register"] == "unknown"
    ]
    assert unknowns, "a briefing that never says 'not established' is guessing somewhere"
    for step in unknowns:
        assert step["text"].lower().startswith(
            ("not stated", "not designated", "no outstanding", "not established")
        )


def test_the_tracked_subject_leaves_one_thing_unknown():
    out = run("2026-09-15", "2026-08-31", write=False)
    assert out["tracked"]["unknown_label"] == "NOT STATED IN PUBLIC SOURCES"
    assert "does not estimate" in out["tracked"]["unknown"]
