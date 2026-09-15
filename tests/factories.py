"""Small hand-made snapshots, so the pipeline tests do not depend on the real data."""

from briefing.model import Evidence, Observation, Obligation, Snapshot


def evidence(eid="ev-1", published="2026-09-01", url=None, kind="sec_filing"):
    return Evidence(
        id=eid,
        kind=kind,
        title=f"Document {eid}",
        published=published,
        url=url or f"https://www.sec.gov/Archives/edgar/data/1001907/{eid}.htm",
        retrieved="2026-09-15",
        accepted=f"{published}T12:00:00Z",
    )


def snapshot(as_of="2026-09-15", evidences=(), observations=(), obligations=()):
    snap = Snapshot(as_of=as_of, company="Astrotech Corporation", ticker="ASTC", cik="0001001907")
    for e in evidences:
        snap.evidence[e.id] = e
    for o in observations:
        snap.observations[o.id] = o
    for o in obligations:
        snap.obligations[o.id] = o
    snap.check()
    return snap


def basic(as_of="2026-09-15", due="2026-09-28"):
    ev = evidence()
    obs = Observation(id="obs-1", evidence="ev-1", quote="a quoted passage", fact="a fact")
    ob = Obligation(
        id="obl-1",
        what="File the annual report",
        due=due,
        rule="ninety days after the fiscal year end",
        owner="Interim Chief Financial Officer",
        evidence="ev-1",
    )
    return snapshot(as_of, [ev], [obs], [ob])
