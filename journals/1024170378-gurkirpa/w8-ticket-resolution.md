# Week 8 : A Model That Could Only Be Run From The Inside

# Two Copies Of One Formula

## Error:

The plan for this week was a live dashboard, with a panel where a
reader moves a slider (more fires, less wind, higher humidity) and
sees what the model would forecast instead. That needs the model
to run in the browser, from plain readings.

The model itself is easy to move: a ridge fit is an intercept and
nine weights, already saved in `data/model.json`. The part that
could not be moved was the step before it, where readings become
inputs. It only existed inside the training loop in
`features.build()`, written straight into the loop body after the
date bookkeeping:

``` python
        values = {
            "cams_log": math.log1p(cams),
            "obs_recent_log": (math.log1p(obs_recent)
                               if obs_recent is not None else None),
            ...
        }
        if use_weather:
            ...
            if speed is not None and bearing is not None:
                rad = math.radians(bearing)
                u, v = -speed * math.sin(rad), -speed * math.cos(rad)
```

No function took a reading and returned an input. The readings
themselves were not kept either: once a row's vector was built,
the CAMS figure, the station reading and the fire count it came
from were gone.

## Relevant Context

After the prototype review the project's direction was to make the
work visible rather than only correct. The dashboard is the first
part of that: tomorrow's number on the CPCB scale, a map of
yesterday's fires against tomorrow's wind, the full history, and
the input-by-input breakdown with sliders.

The breakdown is exact for this model. In log space the forecast
is the intercept plus one term per input, so each term is that
input's push on the number. The sliders reuse the same arithmetic.

## Key Observation

The obvious fix is to copy the arithmetic into JavaScript. The
problem with a copy is that it can be wrong without looking wrong.
A slider that gives a bad number looks exactly like one that gives
a good number.

Even a careful copy is not guaranteed to match. Python's
`math.radians(x)` computes `x * (pi / 180)`. The natural
translation, `x * Math.PI / 180`, computes `(x * pi) / 180`, which
can round differently in the last bit. That is harmless on its
own, but it means the two versions cannot be compared for exact
equality, and a check that only looks at the final forecast would
not say which input had drifted.

So the copy was going to happen anyway. What it needed was a
single source to copy from, and a check that runs every time the
page loads.

## Solution

+  `features.transform(raw, burning, names)` is now the only place
   where readings become model inputs. `build()` collects the raw
   readings for a row and calls it. Nothing else changed:
   `metrics.json` and `model.json` came out identical before and
   after.
+  Each row keeps its readings in `Sample.raw`, along with the day
   the station reading and the fire count came from, so the page
   can say "24.7 on 17 October" rather than just "24.7".
+  `pages.py` writes the raw readings, the vector and the fitted
   model into `docs/dashboard/data.json`. A test checks that
   `transform(raw)` rebuilds the vector exactly after a JSON round
   trip.
+  `dashboard.js` has its own `transform()`, written line for line
   against the Python one. On load, the page rebuilds tomorrow's
   vector, compares it with the pipeline's input by input to a
   relative tolerance of `1e-9`, and checks it gets the same
   forecast. If either check fails, the sliders stay off and the
   page says which input disagreed.
+  The bars shown before anyone touches a slider come from
   Python's breakdown, not the browser's, so a failed check only
   costs the sliders.

To test the check, `cams_log` was nudged by 0.01 in a copy of
`data.json`. The sliders turned off and the note read:

```
The sliders are switched off because the page and the pipeline
disagree on cams_log.
```

With the real file, the panel matches the pipeline. The forecast
for 24 October is 41. With yesterday's fires raised from 161 to 3000 it
becomes 49, and with humidity at 100% it falls to 25. Those are
the model's own weights at work, which the page states plainly:
they describe what has tended to come with cleaner or dirtier days
at this station, not the chemistry.

Two smaller changes came out of the same work:

+  The daily ingest already downloaded every FIRMS fire detection
   and then kept only the count. It now also writes the last two
   days' positions to `data/fires.json` for the map.
+  `evaluate.py` now keeps the backtest's day-by-day forecasts in
   `data/backtest.json`, so the history chart reaches back through
   the 2025 burning season instead of starting in September.

The test suite went from 100 to 117.

**Because**

Every serious problem in this project so far has been a silent
one: a job that reported success while fetching nothing, a
baseline that quietly read the future, a forecast that was simply
not there. A browser copy of the model would have been the same
kind of risk, in a place no test run would ever look. The check
now runs in the reader's browser on every visit, which is the
only place that copy actually runs.

Building the page also surfaced one number worth stating. The
likely range held the measured value on 15 of the 27 live days
scored so far, against the roughly four in five it is sized for.
The page prints the 15 of 27 rather than the target. Resizing the
range from out-of-sample errors belongs with next week's model
comparison.
