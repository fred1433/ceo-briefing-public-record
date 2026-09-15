# CEO Corporate Intelligence Briefing, built from the public record

A daily briefing for the chief executive of a listed company, assembled from documents
anyone can read: filings accepted by EDGAR, press releases, and the company's own pages.
It answers seven questions about each item, in this order:

> WHAT HAPPENED, WHAT CHANGED, WHY IT MATTERS, WHO OWNS IT, WHAT IS LATE,
> WHAT DECISION IS REQUIRED, WHAT TO DO NEXT

and it keeps four registers apart, visibly, because they are not the same thing:

| register | what it is | rule |
|---|---|---|
| **fact** | what a public document says | carries the link and the passage, word for word, or it does not print |
| **interpretation** | what we read into it | labelled as ours, and phrased so the reader can disagree |
| **recommended action** | what to do about it | operational: an owner, a date, a decision. Never financial, never about the stock |
| **not established** | what the sources do not settle | said in fixed words rather than guessed: no owner the record does not designate, nothing called late that the record does not show to be late, no invented task |

The fourth register is the one that keeps the other three honest, and the build
refuses any other wording for it.

The worked example in `data/` is **Astrotech Corporation (Nasdaq: ASTC, CIK 0001001907)**,
on two dates, August 31 and September 15, 2026. Both were reconstructed on September 15
from what was public on each date: a historical replay, not two briefings delivered on
the day. The second reports what moved and refuses to repeat what did not.
Published page: https://astrotech-briefing.theaipipe.com

This is the briefing engine, demonstrated on a public record. The internal version, on
Outlook, SharePoint and OneDrive, remains to be built. Nothing here is an Astrotech
publication, nothing here is non-public, and nothing here is investment advice.

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

**diff** reports three kinds of change, and the third is the one most systems miss.
A document and an exhibit furnished with it share one event id, so a press release and
the filing it is attached to are one change and not two:

- `appeared` a document or a claim that was not in the previous snapshot
- `status`   an obligation that crossed a date line: open to late, open to closed, not open to open
- `drift`    a source that did **not** change while an event says it should have

A document changing is a corporate event. A document *not* changing, past a tolerance, is
also one. The tolerance for a board or officer change the company's own pages have not
caught up with is 60 days, in `diff.RECONCILIATION_TOLERANCE_DAYS`, and it is what put the
fourth item of the September 15 briefing on the page. It fires on the run that crosses the
tolerance and then goes quiet: a reconciliation that stays true is not news twice.

A live page carries no version history, so it cannot stand as evidence of an earlier
state. Company pages enter the snapshot of the day they were read and no earlier one,
which is why the August 31 snapshot has none.

**rank** is arithmetic: weights per change kind, plus a term for how close a deadline is.
The same snapshot always produces the same order, which is why `verify` can compare a fresh
build against the committed one byte for byte.

## Where the model sits, and what is replayable

There is no API call in this repository, in its tests, or in its build. The classification
and the ranking are arithmetic. The wording of each item lives in `data/editorial/<date>.json`
and **is a pre-computed output, written by hand at build time for this public example.**

In production that editorial layer is the model, and it is the only place a model appears.
It runs inside the customer's own approved environment, against their own snapshot, and it
sees exactly what the snapshot holds: quoted passages and their links. The prompt it
receives and the shape it must return are in `data/editorial/PROMPT.md` and
`data/editorial/SCHEMA.json`, unchanged from what produced the two files here. Everything
around it stays as it is, which is the point: the part that can be wrong is small, bounded,
and always shown next to the passage it is reading.

What can be replayed, and how:

| | where |
|---|---|
| the command that produced each file | `data/run.json`, and the `build` lines above |
| the inputs, kept | `data/snapshots/`: every document, its URL, its acceptance timestamp, the day it was read, and every passage quoted from it |
| the prompt and the output schema | `data/editorial/PROMPT.md`, `data/editorial/SCHEMA.json` |
| the trace of the run that produced the committed files | `data/run.json`: commit, digests of inputs and outputs, counts, model calls |
| that the outputs still match their inputs | `briefing.cli verify`, byte for byte, in CI |
| that the quotations still match the documents | `tools/verify_sources.py`, against the live web |

There is no connector in this repository and no imitation mailbox. The fixtures in
`tests/factories.py` are invented documents with invented identifiers, used to exercise the
mechanism; none of them is presented as an Astrotech event.

## Checking the work

`tools/verify_sources.py` re-downloads every cited document and asserts that every quoted
passage is still in it, word for word. Last run on the September 15 snapshot: **68 passages
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
| `test_witnesses.py` | the two witnesses below, plus: a filing and its exhibit are one event, no quarterly figure is republished as news, and the "not established" register is actually exercised |

## Two witnesses

**Silence.** The same sources, read twice, produce no item and no alert. The August
briefing replays the alert rule over its own window and reports that it did not fire. A
system that cannot stay quiet cannot be believed when it speaks.

**Correction.** The Form 10-Q/A of August 6, 2026 states one correction, the number of
shares issuable on conversion of the Series D preferred stock. The briefing reports that
correction and republishes none of the quarter's figures as though they were news. The
test asserts both halves.

## Reaching an internal tenant

The same four record types hold for Microsoft 365. An Evidence becomes a message, a file
version or a meeting; its URL becomes the deep link back to the item; its acceptance
timestamp becomes the sent or modified time. The snapshot, the diff, the ranking and the
sourcing rule do not change at all.

What does change is the access, and it is a set of decisions to settle before any
ingestion rather than a set of guarantees:

- **Exchange**: application access, read only, restricted to the authorized mailboxes
  through Application RBAC, with a check that no wider tenant consent quietly overrides
  the restriction. Delegated access is the wrong tool here: an Outlook delegated
  subscription reaches the signed-in user's own mailbox and no further.
- **SharePoint and OneDrive**: selected permissions (`Sites.Selected`) with explicit
  grants, site by site.
- **The rest**: an approved environment and an approved model provider, named recipients,
  a retention window, a way to revoke, and a trace of what was read.

Nothing in this repository touches or simulates such a tenant.

## Running it

The engine is one half. The other half is watching the collection, checking the outputs
that matter before they reach a desk, tuning the thresholds as they turn out to be wrong,
handling incidents, and keeping the integrations alive as the tenant changes. Those are
offered as components of an operated service, priced and scoped in conversation. What a
first conversation settles is availability and where human judgment sits.

MIT licensed.
