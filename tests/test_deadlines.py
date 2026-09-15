"""A date that has gone by is reported as late, and a window is reported as shut.

The distinction matters to the reader: a duty the company owes is late; a window
that closes on somebody else is closed, and calling it late would be wrong.
"""

from briefing.diff import diff
from briefing.model import Obligation
from briefing.rank import rank
from tests.factories import basic


def _obligation(**kw):
    base = dict(
        id="obl-x",
        what="A duty",
        due="2026-09-10",
        rule="a public rule",
        owner="Corporate Secretary",
        evidence="ev-1",
    )
    base.update(kw)
    return Obligation(**base)


def test_a_passed_duty_is_late():
    assert _obligation().status("2026-09-15") == "late"
    assert _obligation().days_left("2026-09-15") == -5


def test_a_duty_still_ahead_is_open():
    assert _obligation(due="2026-09-28").status("2026-09-15") == "open"


def test_a_passed_window_is_closed_not_late():
    window = _obligation(kind="window", window_opens="2026-08-14", due="2026-09-13")
    assert window.status("2026-08-31") == "open"
    assert window.status("2026-08-01") == "not_open"
    assert window.status("2026-09-15") == "closed"


def test_a_discharged_duty_is_closed():
    assert _obligation(closed_by="ev-1").status("2026-09-15") == "closed"


def test_going_late_outranks_everything_else():
    before = basic("2026-09-09")
    after = basic("2026-09-15")
    for snap, as_of in ((before, "2026-09-09"), (after, "2026-09-15")):
        snap.obligations["obl-1"] = _obligation(id="obl-1", due="2026-09-10")
    changes = diff(before, after)
    late = [c for c in changes if c.kind == "status" and c.after == "late"]
    assert late and late[0].before == "open"
    assert rank(after, changes)[0].key == "obl-1"
