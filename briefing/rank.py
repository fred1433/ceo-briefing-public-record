"""Turn changes and obligations into a ranked shortlist.

The scoring is arithmetic and auditable. It answers one question: of everything on
the public record today, which handful reaches the Chairman/CEO's desk.

Nothing here calls a language model. Ordering is decided by dates and rule weights,
so the same snapshot always produces the same order.
"""

from __future__ import annotations

from dataclasses import dataclass

from .diff import Change
from .model import Snapshot

WEIGHT = {
    "status:open->late": 100,
    "status:open->closed": 70,
    "status:not_open->open": 60,
    "appeared": 55,
    "drift": 50,
    "standing": 30,
}

# A deadline inside this many days is escalated even when nothing about it changed.
HORIZON_DAYS = 120


@dataclass
class Candidate:
    key: str
    score: int
    reason: str
    evidence: tuple[str, ...]


def rank(current: Snapshot, changes: list[Change]) -> list[Candidate]:
    out: list[Candidate] = []
    for c in changes:
        if c.kind == "status":
            if c.before is None:
                # First run. There is no transition to report, only a standing
                # deadline, which the second loop scores by how close it is.
                continue
            key = f"status:{c.before}->{c.after}"
            score = WEIGHT.get(key, 40)
            reason = f"obligation moved from {c.before} to {c.after}"
        elif c.kind == "drift":
            score = WEIGHT["drift"]
            reason = "the company's own page has not reflected a filed change"
        else:
            score = WEIGHT["appeared"]
            reason = "new on the public record since the previous snapshot"
        out.append(Candidate(c.key, score, reason, c.evidence))

    seen = {c.key for c in out}
    for oid, ob in current.obligations.items():
        if oid in seen:
            continue
        if ob.status(current.as_of) in ("open", "late"):
            left = ob.days_left(current.as_of)
            if left <= HORIZON_DAYS:
                score = WEIGHT["standing"] + max(0, HORIZON_DAYS - left) // 4
                out.append(
                    Candidate(oid, score, f"deadline in {left} days", (ob.evidence,))
                )

    out.sort(key=lambda c: (-c.score, c.key))
    return out
