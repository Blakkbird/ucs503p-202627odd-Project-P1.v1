# Week 6 : A Forecast That Was Not There

# Reading One Fixed Day From A Feed That Publishes In Batches

## Error:

Back after the mid-semester tests, the daily job looked healthy.
It had committed every morning since 15 September without a
single gap, and the workflow was green more often than not. The
forecast record told a different story:

```
target days   7 Sep .. 7 Oct      31
forecasts     issued               21
missing                            10, including 6 and 7 Oct
```

A third of the days had no forecast at all. Worse, on 6 October
the project page said "Tomorrow in Patiala: Monday 05 October" and
showed Monday's number. It was Tuesday. The page was presenting a
stale forecast as the next one.

## Relevant Context

The forecast for day D needs the freshest observation published
by the morning of D-1. Week 3 measured the CPCB lag at three days,
so `features.py` read the observation from D-4:

``` python
recent = _observed_upto(obs, cutoff, 1)   # the cutoff day only
obs_recent = recent[-1] if recent else None
```

If that one day was missing, the row had no recent observation,
the feature vector was incomplete, and `predict.py` skipped the
day. It did fail the run, as designed in week 4, so these were
not silent. They were just frequent enough to look like noise.

The ingest log showed when observations actually arrived:

```
ingested 22 Sep, 25 Sep, 30 Sep, 3 Oct, 4 Oct, 6 Oct
```

## Key Observation

The lag is not three days. It is three days *on average*. The
feed publishes in batches every two to five days, and now and
then a day lands with too few hours to count under the 16-hour
rule (2 October came in at 14). A rule that needs one specific
day is therefore only satisfied on the mornings a batch happens
to land in time.

The code below the lookup already knew this. The loop that works
out how old the reading is walked back several days looking for
one. The lookup itself never did. The two had been written with
different assumptions and nothing compared them.

Two smaller faults turned up in the same area:

+  The ingest only ever filled a *blank* observation. A thin day
   published at 14 hours was kept at 14 hours forever, even if the
   station later sent the rest.
+  The page fell back to the newest forecast on record when
   tomorrow's was missing, under a heading that still said
   tomorrow.

And one that had not happened yet. A page test built on September
records checked that the chart drew. The chart only shows the
last 45 days, so from about 22 October the test would fail, and
the daily workflow runs the tests before it commits. The data
would have stopped being saved with nothing obviously wrong.

## Solution

Walk back, but only backwards, and only so far:

``` python
recent = _observed_upto(obs, cutoff, config.OBS_LOOKBACK_DAYS + 1)
obs_recent = recent[-1] if recent else None
```

`OBS_LOOKBACK_DAYS = 3` lets the reader take the freshest valid
reading between D-4 and D-7. Training rows use the same rule, so
the fit and the forecast see the same kind of input. A test holds
the ordering between this and the staleness alarm: latency plus
lookback is 6, the alarm is at 7, so the forecast runs out of
readings before the alarm says the feed is dead.

The other three:

+  `merge_obs` replaces a thin reading when the same day comes
   back with more hours. Full readings are never touched.
+  The live record only scores days that are valid labels, the
   same days the backtest scores. Two scores already attached
   from thin days were withdrawn.
+  `predict.py` writes a status block, and the page shows a grey
   "No forecast" card with the reason instead of yesterday's
   number. `forecast_page` takes `today` as an argument so the
   tests no longer depend on the clock.

The backtest moved from 58 scored days to 63 and its error barely
changed. That was the point: the forecasts now exist.

**Because**

The withdrawn scores need saying plainly. Both thin days, 27
September and 2 October, were misses, so withdrawing them moved
the live error from 6.35 to 5.48. The rule is the right one,
because the backtest has excluded thin days since week 5 and the
two records should be judged the same way. But a change that
improves a headline number is exactly the kind that should be
written down next to the number, so it is here.

The wider lesson is the same one as week 4 from the other side.
There, a failure was invisible because every symptom looked like
success. Here the failures were visible, a red run every few days,
and still went unexamined because each one looked like a one-off.
Counting them is what showed they were a pattern.
