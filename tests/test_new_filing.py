"""A document added to the record becomes an item, and the item carries its link."""

from briefing.diff import diff
from briefing.rank import rank
from briefing.render import build
from tests.factories import basic, evidence, snapshot
from briefing.model import Observation


def _with_new_filing():
    # The standing deadline is far out, so it does not compete with fresh news.
    before = basic("2026-09-14", due="2026-12-20")
    after = basic("2026-09-15", due="2026-12-20")
    new = evidence("ev-2", published="2026-09-15", url="https://www.sec.gov/Archives/edgar/data/1001907/new.htm")
    after.evidence["ev-2"] = new
    after.observations["obs-2"] = Observation(
        id="obs-2", evidence="ev-2", quote="the new passage", fact="something new happened"
    )
    after.check()
    return before, after


def test_new_filing_shows_up_as_a_change():
    before, after = _with_new_filing()
    changes = diff(before, after)
    assert {c.key for c in changes} == {"ev-2", "obs-2"}


def test_new_filing_outranks_a_distant_deadline():
    before, after = _with_new_filing()
    order = [c.key for c in rank(after, diff(before, after))]
    assert order.index("ev-2") < order.index("obl-1")


def test_rendered_item_carries_the_link_and_the_quote():
    before, after = _with_new_filing()
    editorial = {
        "headline": "h",
        "scope": "s",
        "items": [
            {
                "key": "ev-2",
                "headline": "Something new",
                "chain": {
                    "what_happened": {"text": "A document appeared.", "sources": ["obs-2"]},
                    "next_step": {"text": "Read it."},
                },
            }
        ],
    }
    out = build(after, before, editorial)
    source = out["items"][0]["chain"][0]["sources"][0]
    assert source["url"] == "https://www.sec.gov/Archives/edgar/data/1001907/new.htm"
    assert source["quote"] == "the new passage"
