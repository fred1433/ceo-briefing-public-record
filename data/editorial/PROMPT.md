# The editorial layer

Everything else in this repository is arithmetic: fetch, snapshot, diff, rank, render.
This one layer turns a ranked change into the words a reader sees.

**In this repository that layer is a pre-computed output.** The two files
`2026-08-31.json` and `2026-09-15.json` were written by hand at build time and
committed. No model is called when the briefings are built, when the tests run, or
when the page is deployed. That is a deliberate property of a public sample, and
saying otherwise would be the first thing worth distrusting here.

**In production this layer is the model**, running inside the customer's own
approved environment, on their own snapshot. It receives the prompt below and
returns the schema in `SCHEMA.json`. Nothing else in the pipeline changes.

## What the model is given

For one ranked change: the change kind (`appeared`, `status`, `drift`), the
obligation or document it concerns, and the observations attached to it. Each
observation is a quoted passage, the document it came from, that document's date
and its URL. It is given nothing else: no page text, no prior briefing, no
retrieval at its own initiative.

## The prompt

> You are writing one item of a daily briefing for the chief executive of a listed
> company, from the records below and from nothing else.
>
> Answer only the questions the records let you answer, in this order: what
> happened, what changed since the previous state, why it matters, who owns it,
> what is late, what decision is required, what to do next. Leave out any of them
> you cannot answer from the records. Do not invent a task.
>
> Three rules decide most of it:
>
> 1. A **fact** cites the record it came from. If you cannot point at a passage,
>    it is not a fact and it does not go in.
> 2. An **interpretation** is labelled as one and phrased so the reader can
>    disagree with it.
> 3. Anything the records do not establish is written as **not established**, in
>    these words and no others: "Not stated in public sources." for an owner,
>    "Deadline passed; completion unverified." for a deadline you cannot confirm
>    was met, "No outstanding decision established from these sources." for a
>    decision. Never name an owner the records do not designate. Never call
>    something late that the records do not show to be late. Never manufacture an
>    action for the reader to perform.
>
> A recommended action, when there is one, is operational: an owner, a date, a
> decision. Never financial, never about the value of a security, never a view on
> funding, dilution or how long the cash lasts.
>
> Return the schema in SCHEMA.json and nothing else.

## Regenerating

```bash
python3 -m briefing.cli build  --date 2026-08-31
python3 -m briefing.cli build  --date 2026-09-15 --previous 2026-08-31
python3 -m briefing.cli verify --date 2026-09-15 --previous 2026-08-31
```

`verify` rebuilds from the committed snapshot and editorial and compares byte for
byte with the committed briefing. The inputs are kept: `data/snapshots/` holds every
document read, its URL, its EDGAR acceptance timestamp, the date it was retrieved,
and every passage quoted from it. `data/run.json` records the run that produced the
committed files. `tools/verify_sources.py` re-downloads each document and checks
that each passage is still in it, word for word.
