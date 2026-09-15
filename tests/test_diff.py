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


def test_a_repeated_item_must_say_what_is_new_about_it():
    """Repeating an item is allowed only when the briefing names the delta.

    Straight from the reader's brief: identify significant changes rather than
    repeatedly telling me the same information every day. An item carried over
    with nothing new to say is the failure mode, so it fails the build.
    """
    from briefing.cli import run

    out = run("2026-09-15", "2026-08-31", write=False)
    carried = [i for i in out["items"] if i["carried_over"]]
    assert carried, "the September briefing carries two items over on purpose"
    for item in carried:
        assert item["new_since_previous"], f"{item['key']} repeats itself with no delta"
