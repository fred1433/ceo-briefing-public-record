"""The same snapshot twice must produce nothing new.

This is the test that protects the reader from the failure he named himself:
a briefing that repeats yesterday's briefing.
"""

from briefing.diff import diff
from tests.factories import basic


def test_same_snapshot_twice_reports_nothing():
    snap = basic()
    assert diff(snap, snap) == []


def test_first_run_reports_everything_once():
    snap = basic()
    changes = diff(None, snap)
    kinds = {c.kind for c in changes}
    assert kinds == {"appeared", "status"}
    assert {c.key for c in changes if c.kind == "appeared"} == {"ev-1", "obs-1"}


def test_a_second_identical_run_after_a_first_reports_nothing():
    first = basic("2026-09-15")
    again = basic("2026-09-15")
    assert diff(first, again) == []
