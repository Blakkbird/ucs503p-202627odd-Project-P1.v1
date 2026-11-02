# Week 9 : A Forecast That Would Not Use What It Had

# A Lag Measured In August, Applied In November

## Error:

On 30 October the daily job issued no forecast for 31 October.
The log said:

```
no forecast for 2026-10-31: incomplete features, missing ['obs_recent_log']
```

and the dashboard told readers the station had not published a
usable reading recent enough to work from. That was not true.
`daily.csv` at that morning's commit held 28 October (34.5 µg/m³,
24 hours) and 29 October (19.0, 24 hours).

Three days later the same rule failed the other way. The forecast
for 3 November was 37, Satisfactory, built from 30 October's 11.4.
Meanwhile 31 October (79.3) and 1 November (106.0) were already in
the table. The burning season had arrived, the job had the
readings that showed it, and the forecast ignored them.

## Relevant Context

Since week 5 the model has only read observations that were
published by the time the forecast goes out. That rule is what
makes the backtest honest. It was written as one constant:

``` python
OBS_LATENCY_DAYS = 3    # measured on 2026-08-17
OBS_LOOKBACK_DAYS = 3   # walk back past a missing or thin day
```

So a forecast for day D read the reading from D-4, or walked back
as far as D-7 if that day was missing. In August that was right:
the feed ran three days behind.

The feed has not stayed still. The `ingested_at` stamps show
when each reading first landed:

```
reading   written to daily.csv
28 Oct    29 Oct 14:16 IST
29 Oct    30 Oct 14:22 IST
30 Oct    31 Oct 14:12 IST
31 Oct    1 Nov 15:02 IST
```

Since late October each day has been published by the next
afternoon.

## Key Observation

The constant was doing two jobs at once. It described the feed,
which had changed. It also kept the information set honest, which
must not change. The fix had to drop the first job and keep the
second.

Setting the lag to one day would not have been enough. The walk
back would still have handed a model trained on two-day-old
readings a five-day-old one whenever the feed slipped back into
batches, and the model would have trusted it like a fresh one.
How much a reading is worth depends on how old it is, so the age
has to be part of which model is used, not just which reading.

## Solution

+  A reading's age is now counted from the target day, so a
   reading from D-2 is two days old. Two is the minimum, because
   the issue day is never over when the job runs.
+  `features.build(age=...)` builds every row at exactly that age,
   with no walking back. A missing reading leaves the row unusable
   for that age's model instead of quietly substituting an older
   one.
+  `features.freshest_age()` finds the youngest valid reading
   actually on file for tomorrow. `evaluate.py` fits the shipped
   model at that age and writes the age into `data/model.json`.
   `predict.py` checks it, and refits if the two disagree.
+  The headline backtest runs at `config.OBS_REFERENCE_AGE = 2`,
   the freshness the feed delivers now. Persistence is scored with
   a reading of the same age, so the comparison stays fair.
+  Each forecast now records `issued_at`, the time it was really
   issued, and the day its reading came from. Commits land between
   12:30 and 15:30 IST although the job is scheduled for 08:00.
   GitHub delays scheduled runs, and the docs now say so.
+  On the morning this is merged, tomorrow's forecast has already
   been frozen by the old model, while the dashboard's breakdown is
   rebuilt from the new one. The two would show different numbers,
   so the breakdown is now left out, with the reason, whenever it
   would not reproduce the forecast on record.

Replaying the last ten mornings on the `daily.csv` each morning's
commit actually had:

```
forecast for   old rule            new rule              observed
31 Oct         none issued         37.7 (age 2)          79.3
1 Nov          47.4                33.0 (age 2)          106.0
3 Nov          37.4                63.3 (age 2)          not yet
```

Headline numbers are in the second ticket below, because a second
fix changed them.

**Because**

The rule was always "only what had been published by issue time".
The constant was an estimate of that, and the estimate went stale
without anything failing loudly. The job missed one forecast and
made the rest from readings older than they needed to be. It now
reads the answer from the data on file instead of from a number
measured in August, and it tells the model how old that answer is.

# A Backtest That Learnt From Days Nobody Had Yet

## Error:

Writing the new age rule into the backtest showed that the
backtest had never kept the rule itself. Each step of the walk
forward trained on every usable row before the target day:

``` python
for i in range(MIN_TRAIN, len(ready)):
    train, target = ready[:i], ready[i]
```

For a target D read at age 2, that training set included D-1,
whose reading is not published until after the forecast goes out.

## Relevant Context

The live forecast never had this problem. `daily.csv` simply does
not contain a reading before it is published, so the live fit can
only learn from what existed. The leak was in the backtest alone,
which made the backtest a little kinder than the service it
describes.

## Key Observation

One or two extra rows out of five hundred sounds harmless. It was
not. With the training set cut to the days actually published, the
backtest MAE at age 2 went from 8.56 to 8.76. The newest rows carry
the current level of the air, which is what a forecast most needs,
and the cross-validated penalty is chosen on that same recent tail.

## Solution

+  `evaluate.published()` returns the rows a forecast for D could
   have learnt from: days up to the one its reading came from.
   `backtest()` trains on those and nothing newer.
+  Each backtest run records `trained_to`, and a test asserts that
   it never passes the reading's day, at more than one age.

The backtest at the new reference age, after both fixes:

```
                     Pawan   persistence, same age   skill   target
calm (394 days)      7.98    9.19                    +13.2%  10%
burning (76 days)   12.85   15.84                    +18.9%  20%
live (60 days)       7.32    9.03                    +18.9%
```

The same model and the same corrected backtest at the freshness the
proposal was written against:

```
reading age   Pawan MAE   persistence MAE   calm    burning
2 days        8.76        10.27             +13.2%  +18.9%
3 days        9.13        11.25             +15.9%  +27.3%
4 days        9.43        12.41             +21.6%  +31.8%
```

The model's error is lower than it has ever been against the live
data. The bar it is measured against moved further: a two-day-old
reading is a much better forecast than a four-day-old one.
Against that stronger bar the calm target is met and the burning
target is a point short.

The test suite went from 117 to 128.

**Because**

A backtest is a promise about how the service would have done. It
can only keep that promise if it follows the same rules as the
service, including the ones nobody wrote down because the live
data enforced them for free.
