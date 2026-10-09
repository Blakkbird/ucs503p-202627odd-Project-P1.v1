# Week 7 : A Model Trained On Summer, Forecasting October

# A Request Limit Mistaken For The Size Of An Archive

## Error:

With the forecast gaps fixed, the first October forecasts could be
scored. They were wrong in a consistent direction:

```
day       forecast   observed
3 Oct     22.3       37.8
5 Oct     22.3       38.1
```

The season had started. CAMS was forecasting 80 to 117 µg/m³,
fire counts upwind had climbed to 89 a day, and Pawan was still
issuing the same 22 it had been issuing in September. Its
predictions across the whole backtest sat between 11 and 23.

## Relevant Context

The model had a `burning` feature for October and November. Its
weight was 0.000, because no training row had ever been in October
or November. The table started on 15 May 2026, seeded by
`scripts/bootstrap.py`:

``` python
PAST_DAYS = 92  # the CAMS archive window Open-Meteo exposes
```

The sensor, 12235142, has reported since February 2025. If the
comment were true, there was simply no forecast archive for last
year's burning season, and nothing to be done until this one
finished.

## Key Observation

The comment was wrong. 92 is the ceiling on the `past_days`
parameter. It is not the extent of the archive. Open-Meteo's own
documentation lists the global CAMS forecast as available from
August 2022 onwards, through explicit `start_date` and `end_date`
parameters. The weather archives go back years as well.

So the whole 2025 burning season had been available since the
first day of the project. The model had been trained on summer and
monsoon alone because of one belief about one parameter, written
down as a fact in a comment, and never checked.

## Solution

`scripts/extend_history.py` fetches observations and CAMS back to
the start of the sensor in chunks and adds the missing days. It
never changes a value already in the table, except where the daily
job would change it too. `scripts/backfill_history.py` then fills
weather and fire counts, and needed three fixes to work at this
size:

+  It stopped at the first weather archive that answered at all.
   Now each day comes from the best archive that has it, and the
   next one down is only asked for what is still missing.
+  It sent the whole range in one request. Now 120 days at a time.
+  Its `--force` flag overwrote weather on live rows too, which
   carry the forecast that was really issued. Now it leaves them
   alone.

It runs as a manual workflow, dry run by default, so it writes to
`master` on GitHub instead of a laptop copy that would have to be
merged against the daily job's commits. The dry run came back
with:

```
rows               149 -> 589     from 2025-02-19
burning season       7 -> 68      every day of Oct and Nov 2025
thin (< 16h)         6 -> 48
```

After the real run, the backtest covers 488 days:

```
                  days   Pawan   operational   skill   target
calm               425    8.11       11.35    +28.5%     10%
burning             63   12.16       19.14    +36.5%     20%
live rows only      47    4.33        7.50    +42.3%
```

Refitted on that history, the backtest forecasts for 3 and 5
October are 33 and 42.

With a burning season to test against, `scripts/compare_models.py`
compared four ways of letting the season change the model. The bar
was written into its docstring before the table was read: clearly
better in burning season, no more than a point or two worse in
calm. None cleared it, so the model is unchanged.

**Because**

The fix took an afternoon. The mistake had cost two months of
training on the wrong half of the year. The difference between
those is the reason to check the limits of a data source against
its documentation rather than against the first request that
worked.

The extended history also showed what the model cannot do. Its
highest forecast over 488 days is 75 µg/m³. The worst observed day
was 141, and of the 9 days that reached the Poor band it flagged
none. A model fitted to minimise average error on a log scale
learns to forecast towards the middle, which is right for an
ordinary day and wrong for a warning. That is the first item in
the improvement plan, and it is in the prototype report next to
the results rather than behind them.
