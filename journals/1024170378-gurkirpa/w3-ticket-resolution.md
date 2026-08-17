# Week 3 : The Baseline We Promised To Beat Reads The Future

# A Publication Lag That Changes What Persistence Means

## Error:

The proposal was presented and accepted this week. It commits to
a 10% reduction in MAE against persistence outside the burning
season and 20% during it, measured against the number we had
computed: persistence MAE 6.5 µg/m³ over 89 day-pairs.

Building the backtest harness afterwards, the model came out at
7.27 against persistence at 6.12 on the same 46 days. Losing to
the baseline is a normal result for a first fit. What was not
normal was that the model had no way to reach that baseline even
in principle.

## Relevant Context

Persistence predicts day D using the observation from D-1. The
forecast for D is issued on the morning of D-1. So persistence
needs a reading from the same day the forecast goes out.

Checking what the feed had actually published, on 17 August:

```
2026-08-15   freshest observation available: 2026-08-14   (lag 1)
2026-08-16   freshest observation available: 2026-08-14   (lag 2)
2026-08-17   freshest observation available: 2026-08-14   (lag 3)
```

The CPCB station publishes late. At 09:00 on D-1 the newest
reading is roughly D-4. The observation persistence uses does not
exist yet at the moment we have to commit to a forecast.

The proposal's 6.5 was computed from the finished table, where
every day is filled in. That is fine as a description of the
record. It is not a description of anything reachable at issue
time.

## Key Observation

The baseline and the model were being scored on different
information. Persistence was allowed to read a value from the
future relative to when the forecast is made; the model was not.
Any comparison between the two was measuring the publication lag
rather than the modelling.

Once the model was restricted to the same information persistence
gets — freshest available reading, roughly D-4 — the ordering
inverted:

```
model                       MAE 7.27
persistence (obs D-1)       MAE 6.12
persistence (obs available) MAE 8.76
```

Both numbers are true. The model beats the baseline it shares an
information set with by 17%, and loses to the textbook one by 19%.

The second worrying thing was smaller and separate. The daily job
averaged wind bearings arithmetically. Bearings are circular:
350° and 10° are twenty degrees apart and average to 180°, which
points the opposite way. Every day with wind crossing north was
recording a bearing that was roughly backwards.

## Solution

Report persistence twice, and say which is which:

``` python
"persistence": [(s.y, s.persistence) for s in rows],
"persistence_operational": [(s.y, s.persistence_op) for s in rows],
```

`config.OBS_LATENCY_DAYS` holds the measured lag, and
`features.py` refuses to read any observation newer than
`issue_date - OBS_LATENCY_DAYS`. There is a test that asserts it,
using a synthetic table where each day's observation is its own
day number, so a leaked value names the day it leaked from.

Wind is now resolved into components before averaging and
converted back:

``` python
u = sum(-s * sin(radians(b)) for s, b in hours) / len(hours)
v = sum(-s * cos(radians(b)) for s, b in hours) / len(hours)
bearing = degrees(atan2(-u, -v)) % 360
```

350° and 10° now average to 0° instead of 180°.

**Because**

The useful lesson is about when a baseline is measured rather than
how. Persistence is trivially correct as arithmetic and we
computed it correctly. It was wrong as a *target* because it was
computed over the completed record instead of over what was
knowable at forecast time, and nothing about the number itself
showed that. A baseline is not just a formula, it is a formula
plus an information set, and the second half is easy to leave
unstated and then quietly violate.

Finding this in week three costs a paragraph in the report. It
would have been a much worse thing to discover in November with
the evaluation already written. Building the backtest before the
model, rather than after, is what surfaced it — the harness had
nothing to prove and so had no reason to flatter anything.

The wind bug is a plainer point: a mean is only meaningful if the
quantity is linear, and degrees are not. It had been sitting in
the ingest since week one, producing values that were well formed,
in range, and pointing the wrong way.
