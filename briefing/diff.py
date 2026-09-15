"""What changed between two snapshots.

Three kinds of change, and one that most systems miss:

  appeared   a document or a claim that was not in the previous snapshot
  status     an obligation that crossed a date line (open -> late, open -> closed,
             not_open -> open)
  drift      a source that did NOT change while an event says it should have

`drift` is the one the CEO asked for without naming it: a document changing is a
corporate event, and a document not changing, past a tolerance, is one too.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from .model import Snapshot


@dataclass(frozen=True)
class Change:
    kind: str  # appeared | status | drift
    key: str  # evidence / observation / obligation id
    detail: str
    evidence: tuple[str, ...]  # evidence ids that carry the change
    before: str | None = None
    after: str | None = None


# A board or officer change that the company's own pages have not reflected after
# this many days is reported. The tolerance is deliberately generous: a website
# lagging a filing by a week is housekeeping, lagging it by two months is a fact.
RECONCILIATION_TOLERANCE_DAYS = 60


def diff(previous: Snapshot | None, current: Snapshot) -> list[Change]:
    changes: list[Change] = []
    prev_ev = set(previous.evidence) if previous else set()
    prev_obs = set(previous.observations) if previous else set()

    # One corporate event, one change. A press release furnished as an exhibit to
    # the filing it accompanies is the same event as the filing: reporting both
    # would be the "twice-told news" the reader complains about.
    seen_events: set[str] = {current.evidence[e].event_id for e in prev_ev if e in current.evidence}
    for eid, ev in sorted(current.evidence.items()):
        if eid in prev_ev or ev.event_id in seen_events:
            continue
        seen_events.add(ev.event_id)
        documents = tuple(
            sorted(k for k, v in current.evidence.items() if v.event_id == ev.event_id)
        )
        changes.append(
            Change(
                kind="appeared",
                key=ev.event_id,
                detail=f"{ev.title} ({ev.published})",
                evidence=documents,
            )
        )
    for oid, obs in current.observations.items():
        if oid not in prev_obs:
            changes.append(
                Change(kind="appeared", key=oid, detail=obs.fact, evidence=(obs.evidence,))
            )

    for oid, ob in current.obligations.items():
        after = ob.status(current.as_of)
        before = None
        if previous and oid in previous.obligations:
            before = previous.obligations[oid].status(previous.as_of)
        if before != after:
            changes.append(
                Change(
                    kind="status",
                    key=oid,
                    detail=ob.what,
                    evidence=(ob.evidence,),
                    before=before,
                    after=after,
                )
            )

    changes.extend(_drift(current, previous))
    changes.sort(key=lambda c: (c.kind, c.key))
    return changes


def _drift(current: Snapshot, previous: Snapshot | None) -> list[Change]:
    """A page that should reflect an event and does not, past the tolerance.

    It is a change on the run that crosses the tolerance, and standing state on
    every run after that: a reconciliation that stays true is not news twice.

    A reconciliation is declared in the snapshot as an observation id pair:
    `reconcile:<event-observation>:<page-evidence>`. The rule owns the date maths,
    nothing else.
    """
    out: list[Change] = []
    today = dt.date.fromisoformat(current.as_of)
    for oid, obs in current.observations.items():
        if not oid.startswith("reconcile:"):
            continue
        _, event_obs_id, page_ev_id = oid.split(":", 2)
        event_obs = current.observations.get(event_obs_id)
        page_ev = current.evidence.get(page_ev_id)
        if event_obs is None or page_ev is None:
            continue
        event_ev = current.evidence[event_obs.evidence]
        happened = event_obs.occurred or event_ev.published
        age = (today - dt.date.fromisoformat(happened)).days
        already = False
        if previous is not None:
            before = (
                dt.date.fromisoformat(previous.as_of) - dt.date.fromisoformat(happened)
            ).days
            already = (
                before >= RECONCILIATION_TOLERANCE_DAYS and page_ev_id in previous.evidence
            )
        if age >= RECONCILIATION_TOLERANCE_DAYS and not already:
            out.append(
                Change(
                    kind="drift",
                    key=oid,
                    detail=f"{obs.fact} ({age} days)",
                    evidence=(event_obs.evidence, page_ev_id),
                    before=happened,
                    after=page_ev.retrieved,
                )
            )
    return out
