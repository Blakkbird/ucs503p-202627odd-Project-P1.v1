# Week 5 : A Model That Lost To The Baseline It Was Built To Beat

# Leakage That Made The Predictions Worse

## Error:

The correction model had been fitted, backtested and shipped. It
scored an MAE of 6.16 against persistence at 5.03, which is 22.6%
worse than doing nothing at all.

Worse than the number was the shape of the failure. Over the first
six days of live forecasts the station climbed steadily while the
model went the other way:

```
persistence  7.7  ->  13.7  ->  17.7  ->  23.2  ->  25.9
forecast    15.8  ->  15.7  ->  16.5  ->  12.9  ->  15.0
```

On 11 September it predicted 16.5 against an observed 27.8. It was
not noisy. It was confidently wrong in a consistent direction.

## Relevant Context

The fitted weights explained the direction immediately.
`doy_sin` carried +3.31, effectively tied with `cams_log` at
+3.35 — the day-of-year term was as influential as the forecast
being corrected.

With four months of data a day-of-year term cannot separate a
season from a trend. Every row in the training set came from a
period when PM2.5 was falling, so the feature had learnt "later in
the year means cleaner air" and was extrapolating that straight
towards October, which is precisely the month the project exists
to forecast.

Three other features were dead or duplicated. `obs_age` had been
constant at 4.0 since the feed was repaired in week 4.
`obs_recent` and `obs_recent_log` were the same signal entered
twice, and their coefficients had settled into opposite signs.
`obs_mean7` had gone negative, which is not a physical
relationship — a higher weekly average lowering tomorrow's
forecast is a symptom of collinearity, not of atmospheric
chemistry.

Each of these had been added for a defensible reason. None had
been checked after the fact.

## Key Observation

The meteorology columns were not in the fit at all. They had been
backfilled weeks earlier and `use_weather` still defaulted to
False everywhere, so wind, temperature and fire counts — the
features most likely to matter in burning season — had never been
tested.

Switching them on and holding the scored days fixed at 46 gave
4.67 against 3.79, a 19% reduction. It also collapsed `doy_sin`
from +3.31 to +0.59. The seasonal term had been standing in for
meteorology the whole time; given the real thing, it stopped
mattering.

Turning them on is also what exposed the leak. The daily job
refused to issue a forecast:

```
no forecast for 2026-09-14: incomplete features, missing ['fire_log']
```

FIRMS records fire detections against the day they happened. A
target day's own count therefore does not exist on the morning
before, when the forecast goes out. The feature had been reading a
column that, for every training row, was filled in after the fact.

## Solution

`fire_log` now reads the most recent count complete at issue time,
walking back up to a week if the feed has gaps:

``` python
burn_day = issue - timedelta(days=config.FIRE_LATENCY_DAYS)
recent_fires = None
for k in range(7):
    got = fires.get(burn_day - timedelta(days=k))
    if got is not None:
        recent_fires = got
        break
```

Alongside that: `doy_sin`, `doy_cos`, `obs_age`, `obs_recent` and
`obs_mean7` dropped; the fit moved into log space, since PM2.5
spans an order of magnitude and on the raw scale the squared error
was being decided by the worst few days; and days published with
fewer than 16 hourly readings are no longer used as training
labels, 16 being CPCB's own threshold for a valid 24-hour mean
rather than a number chosen here.

```
                       MAE    vs operational persistence
before                6.16              +20.9%
after                 3.29              +28.3%
```

The proposal's calm-season target was 10%.

**Because**

The finding worth recording is what the leak did.

Leakage is taught as the thing that flatters a model — it sees the
answer, scores well in testing, fails in production. This one did
the opposite. Removing it *improved* every metric, and `fire_log`
went from the weakest feature in the model to the third strongest.

The reason is that the leaked value was the wrong value. Fires
burning on the target day are the wrong predictor of that day's
air, because smoke lifted off a field upwind takes the better part
of a day to arrive. Yesterday's fires are what describes tomorrow.
The information-set violation and the physical error were the same
mistake, and fixing one fixed the other.

That inverts the usual reason for being careful about leakage.
Enforcing "only what existed at issue time" is normally framed as
honesty — a constraint accepted at some cost to accuracy. Here it
was not a cost. The constraint pointed at the physically correct
feature, and the version that cheated was worse at the actual job.

The wider lesson is about accumulation. No single decision above
was unreasonable when it was made. A seasonal term is standard. A
lagged observation is obviously useful. A flag that has not fired
yet costs nothing to carry. The model still ended up losing to
persistence, because nine reasonable additions were never
subtracted from, and nothing in the pipeline had been asking
whether a feature was still earning its place.

The backtest had been reporting this for weeks. `skill_vs_persistence`
had read -0.2263 the whole time and nobody had looked at it,
because the number was in a JSON file rather than on a page. That
is the other change this week, and it is not a coincidence that it
came out of the same review.
