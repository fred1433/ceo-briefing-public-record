# CEO Corporate Intelligence Briefing, built from the public record

A daily briefing for the chief executive of a listed company, assembled from documents
anyone can read: filings accepted by EDGAR, press releases, and the company's own pages.
It answers seven questions about each item, in this order:

> WHAT HAPPENED, WHAT CHANGED, WHY IT MATTERS, WHO OWNS IT, WHAT IS LATE,
> WHAT DECISION IS REQUIRED, WHAT TO DO NEXT

and it keeps three registers apart, visibly, because they are not the same thing:

| register | what it is | rule |
|---|---|---|
| **fact** | what a public document says | carries the link and the passage, word for word, or it does not print |
| **interpretation** | what we read into it | labelled as ours, and phrased so the reader can disagree |
| **recommended action** | what to do about it | operational: an owner, a date, a decision. Never financial, never about the stock |

The worked example in `data/` is **Astrotech Corporation (Nasdaq: ASTC, CIK 0001001907)**,
on two dates, August 31 and September 15, 2026. The second briefing reports what moved
and refuses to repeat what did not. Published page: https://astrotech-briefing.theaipipe.com

Nothing in this repository is investment advice, and nothing in it is non-public.

## Run it

```bash
python3 -m briefing.cli build  --date 2026-08-31
python3 -m briefing.cli build  --date 2026-09-15 --previous 2026-08-31
python3 -m briefing.cli verify --date 2026-09-15 --previous 2026-08-31   # rebuilds and compares
python3 -m pytest tests -q
```

No dependencies beyond the standard library. `pytest` for the tests.

## The four record types

```
Evidence      a public document: a date, a URL, an EDGAR acceptance timestamp
Observation   one quoted passage, anchored to exactly one Evidence
Obligation    a dated duty, or a dated window, with the public rule that sets the date
Snapshot      all of the above, frozen at one date
```

An Observation with no Evidence is a build failure, not a judgement call. `Snapshot.check()`
refuses to load a snapshot whose anchors do not resolve, and `render.build()` refuses to
print a fact with no quotation. That is the whole integrity story, and it is four lines long.

## The pipeline

```
sources  ->  snapshot  ->  diff  ->  rank  ->  briefing
```

**diff** reports three kinds of change, and the third is the one most systems miss:

- `appeared` a document or a claim that was not in the previous snapshot
- `status`   an obligation that crossed a date line: open to late, open to closed, not open to open
- `drift`    a source that did **not** change while an event says it should have

A document changing is a corporate event. A document *not* changing, past a tolerance, is
also one. The tolerance for a board or officer change the company's own pages have not
caught up with is 60 days, in `diff.RECONCILIATION_TOLERANCE_DAYS`, and it is what put the
fourth item of the September 15 briefing on the page.

**rank** is arithmetic: weights per change kind, plus a term for how close a deadline is.
The same snapshot always produces the same order, which is why `verify` can compare a fresh
build against the committed one byte for byte.

## Where the model sits

There is no API call in this repository, in its tests, or in its build. The classification
and the ranking are arithmetic. The wording of each item lives in `data/editorial/<date>.json`
and was written by hand for this public example.

In production that editorial layer is the model, and it is the only place a model appears.
It runs inside the customer's own tenant, against their own sources, and it sees exactly
what the snapshot holds: quoted passages and their links. Everything around it stays as it
is here, which is the point: the part that can be wrong is small, bounded, and always shown
next to the passage it is reading.

## Checking the work

`tools/verify_sources.py` re-downloads every cited document and asserts that every quoted
passage is still in it, word for word. Last run on the September 15 snapshot: **64 passages
checked in 23 documents, 0 not found**.

```bash
export SEC_USER_AGENT="Your Company you@example.com"   # the SEC refuses anonymous readers
python3 tools/verify_sources.py data/snapshots/2026-09-15.json
```

It needs the network, so it is not in the required build. It runs on demand and weekly.

## Tests

| file | what it protects |
|---|---|
| `test_diff.py` | the same snapshot twice reports nothing. The reader's own words: *identify significant changes rather than repeatedly telling me the same information every day* |
| `test_new_filing.py` | a document added to the record becomes an item, and the item carries its link and its quotation |
| `test_deadlines.py` | a date gone by is late for a duty and closed for a window, and going late outranks everything else |
| `test_sourcing.py` | no line of the two published briefings without a quoted public document, no dangling source id, no mailbox in the output, and both briefings rebuild byte for byte |

## Reaching an internal tenant

The same four record types hold for Microsoft 365. An Evidence becomes a message, a file
version or a meeting; its URL becomes the deep link back to the item; its acceptance
timestamp becomes the sent or modified time. Delegated permissions through Microsoft Graph,
scoped site by site, an audit trail of what the system read, a retention window, and no
corporate content leaving the tenant. The snapshot, the diff, the ranking and the sourcing
rule do not change at all. Nothing in this repository touches or simulates such a tenant.

MIT licensed.
