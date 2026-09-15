"""Data model.

Four record types, and nothing else:

Evidence      a public document. Has a date, a URL, and a retrieval date.
Observation   one quoted claim, anchored to exactly one Evidence.
Obligation    a dated duty that comes from a public rule or a public commitment.
Snapshot      everything above, frozen at one date.

An Observation without an Evidence is a bug, not a judgement call. The renderer
refuses to print it and `tests/test_sourcing.py` fails the build.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field, asdict
from typing import Any


def _date(value: str) -> dt.date:
    return dt.date.fromisoformat(value)


@dataclass(frozen=True)
class Evidence:
    id: str
    kind: str  # sec_filing | press_release | company_page
    title: str
    published: str  # ISO date the document carries
    url: str
    retrieved: str  # ISO date we read it
    accepted: str | None = None  # EDGAR acceptance timestamp, UTC, when known
    event: str | None = None  # the event this document reports; an exhibit shares
    # its filing's event, so a press release and the filing it is attached to are
    # one corporate event and not two.

    @property
    def event_id(self) -> str:
        return self.event or self.id

    def __post_init__(self) -> None:
        if not self.url.startswith("https://"):
            raise ValueError(f"evidence {self.id}: url must be absolute https")
        _date(self.published)
        _date(self.retrieved)


@dataclass(frozen=True)
class Observation:
    id: str
    evidence: str  # Evidence.id
    quote: str  # verbatim from the document, " [...] " between passages
    fact: str  # the claim, in plain words
    occurred: str | None = None  # when the fact happened, if earlier than the filing

    def __post_init__(self) -> None:
        if not self.quote.strip():
            raise ValueError(f"observation {self.id}: empty quote")


@dataclass(frozen=True)
class Obligation:
    """A dated duty, or a dated window.

    kind="duty"    somebody owes the filing or the decision; past the date it is late
    kind="window"  a period that opens and shuts; past the date it is closed, not late
    """

    id: str
    what: str
    due: str  # ISO date
    rule: str  # the public rule or commitment that sets the date
    owner: str  # a public role, never a private individual's contact
    evidence: str  # Evidence.id
    kind: str = "duty"
    closed_by: str | None = None  # Evidence.id that discharges it
    window_opens: str | None = None

    def status(self, as_of: str) -> str:
        today = _date(as_of)
        if self.closed_by:
            return "closed"
        if self.window_opens and today < _date(self.window_opens):
            return "not_open"
        if today > _date(self.due):
            return "closed" if self.kind == "window" else "late"
        return "open"

    def days_left(self, as_of: str) -> int:
        return (_date(self.due) - _date(as_of)).days


@dataclass
class Snapshot:
    as_of: str
    company: str
    ticker: str
    cik: str
    reconstructed: bool = False
    evidence: dict[str, Evidence] = field(default_factory=dict)
    observations: dict[str, Observation] = field(default_factory=dict)
    obligations: dict[str, Obligation] = field(default_factory=dict)

    @staticmethod
    def load(path: str) -> "Snapshot":
        import json

        raw = json.load(open(path, encoding="utf-8"))
        return Snapshot.from_dict(raw)

    @staticmethod
    def from_dict(raw: dict[str, Any]) -> "Snapshot":
        snap = Snapshot(
            as_of=raw["as_of"],
            company=raw["company"],
            ticker=raw["ticker"],
            cik=raw["cik"],
            reconstructed=raw.get("reconstructed", False),
        )
        for e in raw.get("evidence", []):
            snap.evidence[e["id"]] = Evidence(**e)
        for o in raw.get("observations", []):
            snap.observations[o["id"]] = Observation(**o)
        for o in raw.get("obligations", []):
            snap.obligations[o["id"]] = Obligation(**o)
        snap.check()
        return snap

    def to_dict(self) -> dict[str, Any]:
        return {
            "as_of": self.as_of,
            "company": self.company,
            "ticker": self.ticker,
            "cik": self.cik,
            "reconstructed": self.reconstructed,
            "evidence": [asdict(e) for e in self.evidence.values()],
            "observations": [asdict(o) for o in self.observations.values()],
            "obligations": [asdict(o) for o in self.obligations.values()],
        }

    def check(self) -> None:
        """Every anchor resolves. Called on load, so a broken snapshot never renders."""
        for obs in self.observations.values():
            if obs.evidence not in self.evidence:
                raise ValueError(f"observation {obs.id} points at unknown evidence {obs.evidence}")
        for ob in self.obligations.values():
            if ob.evidence not in self.evidence:
                raise ValueError(f"obligation {ob.id} points at unknown evidence {ob.evidence}")
            if ob.closed_by and ob.closed_by not in self.evidence:
                raise ValueError(f"obligation {ob.id} closed by unknown evidence {ob.closed_by}")
        for ev in self.evidence.values():
            if _date(ev.published) > _date(self.as_of):
                raise ValueError(f"evidence {ev.id} is dated after the snapshot")
