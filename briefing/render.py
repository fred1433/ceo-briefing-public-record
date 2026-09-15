"""Assemble the briefing and refuse anything that is not sourced.

Three registers are kept apart on purpose, because the reader asked for it:

  fact            what a public document says, with the quote and the link
  interpretation  what we read into it, marked as ours
  action          what to do about it, operational and never financial

The wording of each item lives in `data/editorial/<date>.json`. In production that
layer is the model, running inside the customer's own tenant on their own sources.
Here it was written by hand at build time, so the published page makes no API call
at all: see README, "Where the model sits".
"""

from __future__ import annotations

import datetime as dt
import json
from typing import Any

from .diff import Change, diff
from .model import Snapshot
from .rank import rank

STEPS = [
    ("what_happened", "WHAT HAPPENED", "fact"),
    ("what_changed", "WHAT CHANGED", "fact"),
    ("why_it_matters", "WHY IT MATTERS", "interpretation"),
    ("who_owns_it", "WHO OWNS IT", "fact"),
    ("what_is_late", "WHAT IS LATE", "fact"),
    ("decision_required", "WHAT DECISION IS REQUIRED", "action"),
    ("next_step", "WHAT TO DO NEXT", "action"),
]

BANNED = ("upwork", "job posting", "@theaipipe", "hiring", "resume", "candidate")


class SourcingError(RuntimeError):
    pass


def build(current: Snapshot, previous: Snapshot | None, editorial: dict[str, Any]) -> dict[str, Any]:
    changes = diff(previous, current)
    order = {c.key: i for i, c in enumerate(rank(current, changes))}
    change_by_key = {c.key: c for c in changes}

    items = []
    for raw in editorial["items"]:
        key = raw["key"]
        item = _item(current, raw, change_by_key.get(key))
        item["rank"] = order.get(key, 999)
        items.append(item)
    items.sort(key=lambda i: i["rank"])

    out = {
        "as_of": current.as_of,
        "company": current.company,
        "ticker": current.ticker,
        "cik": current.cik,
        "previous": previous.as_of if previous else None,
        "reconstructed": current.reconstructed,
        "headline": editorial["headline"],
        "scope": editorial["scope"],
        "items": items,
        "alerts": [_alert(current, a) for a in editorial.get("alerts", [])],
        "carried": [_carried(current, c) for c in editorial.get("carried", [])],
        "counts": {
            "evidence": len(current.evidence),
            "observations": len(current.observations),
            "obligations": len(current.obligations),
            "changes": len(changes),
            "items": len(items),
            "passages": sum(len(o.quote.split(" [...] ")) for o in current.observations.values()),
        },
        "generated": current.as_of,
    }
    _guard(out)
    return out


def _sources(snap: Snapshot, ids: list[str]) -> list[dict[str, str]]:
    out = []
    for sid in ids:
        obs = snap.observations.get(sid)
        if obs is not None:
            ev = snap.evidence[obs.evidence]
            out.append(
                {
                    "id": sid,
                    "title": ev.title,
                    "published": ev.published,
                    "url": ev.url,
                    "quote": obs.quote,
                    "kind": ev.kind,
                }
            )
            continue
        ev = snap.evidence.get(sid)
        if ev is None:
            raise SourcingError(f"unknown source id {sid!r}")
        out.append(
            {
                "id": sid,
                "title": ev.title,
                "published": ev.published,
                "url": ev.url,
                "quote": "",
                "kind": ev.kind,
            }
        )
    return out


def _item(snap: Snapshot, raw: dict[str, Any], change: Change | None) -> dict[str, Any]:
    chain = []
    for field, label, default_register in STEPS:
        block = raw["chain"].get(field)
        if block is None:
            continue
        register = block.get("register", default_register)
        sources = _sources(snap, block.get("sources", []))
        if register == "fact" and not sources:
            raise SourcingError(f"{raw['key']}.{field}: a fact with no source")
        if register == "fact" and not any(s["quote"] for s in sources):
            raise SourcingError(f"{raw['key']}.{field}: a fact with no quotation")
        chain.append(
            {"field": field, "label": label, "register": register,
             "text": block["text"], "sources": sources}
        )
    ob = snap.obligations.get(raw["key"])
    return {
        "key": raw["key"],
        "headline": raw["headline"],
        "answers": raw.get("answers", []),
        "state": raw.get("state", change.kind if change else "standing"),
        "carried_over": raw.get("carried_over", False),
        "new_since_previous": raw.get("new_since_previous"),
        "due": ob.due if ob else None,
        "days_left": ob.days_left(snap.as_of) if ob else None,
        "status": ob.status(snap.as_of) if ob else None,
        "chain": chain,
    }


def _alert(snap: Snapshot, a: dict[str, Any]) -> dict[str, Any]:
    ev = snap.evidence[a["evidence"]]
    return {
        "evidence": a["evidence"],
        "title": ev.title,
        "url": ev.url,
        "published": ev.published,
        "accepted": ev.accepted,
        "local": a["local"],
        "rule": a["rule"],
        "text": a["text"],
    }


def _carried(snap: Snapshot, c: dict[str, Any]) -> dict[str, Any]:
    ev = snap.evidence[c["evidence"]]
    return {
        "text": c["text"],
        "title": ev.title,
        "url": ev.url,
        "published": ev.published,
        "since_days": (dt.date.fromisoformat(snap.as_of) - dt.date.fromisoformat(ev.published)).days,
    }


def _guard(out: dict[str, Any]) -> None:
    blob = json.dumps(out, ensure_ascii=False).lower()
    for word in BANNED:
        if word in blob:
            raise SourcingError(f"banned term in briefing: {word!r}")
    if "—" in blob:
        raise SourcingError("em dash in briefing")


def to_markdown(b: dict[str, Any]) -> str:
    lines = [f"# CEO Corporate Intelligence Briefing", "",
             f"**{b['company']} ({b['ticker']}) - {b['as_of']}**", "",
             b["headline"], "", f"_{b['scope']}_", ""]
    if b["previous"]:
        lines += [f"Previous briefing: {b['previous']}.", ""]
    for n, item in enumerate(b["items"], 1):
        lines.append(f"## {n}. {item['headline']}")
        if item["carried_over"] and item["new_since_previous"]:
            lines.append(f"*Carried over from {b['previous']}. New since then: {item['new_since_previous']}*")
        lines.append("")
        for step in item["chain"]:
            tag = {"fact": "FACT", "interpretation": "INTERPRETATION", "action": "RECOMMENDED ACTION"}[step["register"]]
            lines.append(f"**{step['label']}** [{tag}]  ")
            lines.append(step["text"])
            for s in step["sources"]:
                q = f' "{s["quote"]}"' if s["quote"] else ""
                lines.append(f"  - {s['title']}, {s['published']}: {s['url']}{q}")
            lines.append("")
    if b["alerts"]:
        lines += ["## Would have alerted you", ""]
        for a in b["alerts"]:
            lines.append(f"- **{a['local']}** {a['text']} (rule: {a['rule']}) {a['url']}")
        lines.append("")
    if b["carried"]:
        lines += ["## Unchanged since the previous briefing, not repeated", ""]
        for c in b["carried"]:
            lines.append(f"- {c['text']} ({c['since_days']} days) {c['url']}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
