# Method

## The problem, precisely

On the morning of day D-1, produce the daily mean PM2.5 at Model
Town for day D.

The word *morning* is doing real work there. It fixes what the
model is allowed to know, and that turns out to be less than the
proposal assumed.

## What is actually available at issue time

The daily job is scheduled for 08:00 IST. GitHub starts scheduled
jobs late when it is busy, and in practice the run lands in the
afternoon, so each forecast records the time it was actually
issued. Four backup runs through the day (`code/due.py`) do the
work again only if that run went out without a forecast, or if by
evening it has not run at all. They never run ahead of it, so a
backup that fires on time cannot forecast from a staler reading.
Whenever the job runs, the CAMS and weather forecasts for tomorrow
are already out. The station's own readings are a different matter.

The CPCB feed runs behind, and by how much has changed over the
semester. On 17 August the newest published day was 14 August,
three days behind. In early October readings arrived in batches
every few days. Since late October each day has been published by
the next afternoon.

For most of the project the lag was a fixed three days, measured
in August. When the feed sped up, that rule kept throwing away
readings the job already had. On 2 November the forecast for the
3rd was built from 30 October's 11.4 µg/m³ while 31 October (79)
and 1 November (106) were already in `daily.csv`. On 30 October
no forecast went out at all: the one day the rule allowed was
thin, and the days behind it had never been published.

So the age of the reading is no longer assumed. It is counted
from the target day, so a reading from D-2 is two days old. That
is the youngest a day-ahead forecast can have, because the issue
day is not over when the job runs. Each morning the job finds the
freshest valid reading on file (`features.freshest_age`) and
forecasts with a model fitted on readings of exactly that age
(`features.build(age=...)`). A model fitted on two-day-old
readings has learnt how much a two-day-old reading is worth, and
it is never handed a five-day-old one. Past `config.OBS_MAX_AGE`,
seven days, there is no forecast.

The headline backtest is run at `config.OBS_REFERENCE_AGE`, two
days, which is what the feed delivers now. The model lab scores
the other ages as well, so a slower feed shows up as a measured
cost.

This matters more than it sounds, because it changes what
"persistence" means.

## Persistence, twice

Persistence normally means *tomorrow equals today*. That is the
number in the proposal: MAE 6.5 µg/m³ over 89 day-pairs. It is a
fair textbook baseline and it is what the marks were promised
against.

It is also not available to us. Predicting D from D-1 requires
knowing D-1, and at issue time we do not. So the backtest reports
both:

- **persistence** — obs on D-1. The textbook bar, and the one the
  proposal targets. Uses information the model cannot have.
- **persistence_operational** — the reading of the same age the
  model gets, two days old at the reference age. The same
  information set the model has.

The first is the honest target. The second is the honest
comparison. Reporting only one of them would be a way of choosing
the answer in advance, so both go in `data/metrics.json`.

Climatology and raw CAMS are carried alongside as sanity checks.
Climatology is computed causally — the mean of everything observed
strictly before the day in question, not the mean of the whole
record, which would leak.

## Backtest

`code/evaluate.py` walks forward one day at a time. For each
target day it fits on every usable row strictly before that day,
predicts one value, and moves on. No shuffled split, because the
rows are a time series and shuffling lets the model see its own
future.

The ridge penalty `alpha` is chosen inside each fit, on the most
recent fifth of that fit's training window. Choosing it once on
the whole record would leak the test period into a
hyperparameter — a small leak, but the kind that quietly inflates
every number downstream.

The first `MIN_TRAIN = 40` rows are used for fitting only, never
scored. Below that the fit is noise.

Reported per run: MAE, RMSE, bias, correlation, and the rate at
which the prediction lands in the correct CPCB National AQI band.
The last one matters because a person reading a forecast wants to
know whether tomorrow is *Satisfactory* or *Poor*, not whether the
error was 7.2 or 7.4.

Scores are split into calm and burning seasons, since the targets
differ and the two regimes barely resemble each other.

## Why ridge, and why by hand

The correction is linear in the features, with an L2 penalty,
fitted through the normal equations and solved by Gaussian
elimination. Roughly eighty lines in `code/model.py`.

scikit-learn would be two lines. It would also put numpy, scipy
and a compiled BLAS in the path of a job that has to run
unattended every morning until November. The model is small enough
that writing it out keeps the whole pipeline standard-library
only, and a fitted model is then just the numbers in
`data/model.json` — reproducible without installing anything.

The features are few and mostly logged, so a linear model is not
obviously the wrong shape. The model lab, below, now tests that
directly: on this much data a random forest, gradient boosting and
a small neural network all score worse than the ridge fit.

## The week 5 review

The first fitted model lost to textbook persistence by 22.6% and,
worse, had started drifting downward while the station was
climbing. Pulling it apart found five separate faults, and the
current model is what came out of fixing them.

- **The meteorology was never switched on.** The backfill had been
  run weeks earlier and the fit was still reading CAMS, lagged
  observations and a seasonal term. Wind and fire counts, the two
  things most likely to matter in October, had never been tested.
- **`doy_sin` and `doy_cos` were not measuring seasonality.** With
  four months of data a day-of-year term cannot tell a season from
  a trend, and these had learnt "PM2.5 falls through the monsoon".
  They carried almost as much weight as the CAMS forecast itself
  and would have kept extrapolating that decline into November.
  Dropped.
- **`obs_recent` and `obs_recent_log` were the same signal twice**,
  split across two coefficients that pulled against each other.
  One kept.
- **`obs_age` had been constant** at 4.0 since the feed was
  repaired, so it contributed nothing but still cost a parameter.
  It is still published with each forecast. Since November it
  picks which model forecasts instead of being fitted on, as
  described above.
- **Thin days were being trained on.** CPCB does not consider a
  24-hour mean valid below 16 hourly readings, and neither should
  the model. Days under that line are recorded and displayed but
  are no longer used as labels, nor fed forward as a later day's
  persistence.

Two further changes did more than any of the above.

**Fitting in log space.** PM2.5 spans an order of magnitude
between a clean day and a burning-season one. On the raw scale the
squared error is decided by the worst few days, and the fit bends
towards them at the expense of the ordinary ones. `log1p` makes
the penalty proportional, which is also how the error is felt: ten
out on a reading of twenty matters, ten out on two hundred does
not.

**Lagging the fire count.** FIRMS records detections against the
day they happened, so a target day's own count does not exist when
its forecast goes out. It was a leak. Fixing it improved the
model, because the physically correct signal was the lagged one
all along — smoke lifted off a field upwind takes the better part
of a day to arrive.

## A year and a half of history

Everything above was first fitted on about a hundred days, all of
them summer and monsoon. The table began on 15 May 2026 because
the bootstrap asked Open-Meteo for `past_days=92`, on the belief
that this was as far back as the CAMS archive went. It was only the
ceiling on that one parameter. The live sensor has reported since
February 2025, so the 2025 burning season had been available from
the start.

It mattered in October. On 3 and 5 October the live forecast was
22 µg/m³ against an observed 38: the model had never seen the
season begin. `scripts/extend_history.py` pulled the table back to
19 February 2025, and every day of October and November 2025 came
with it. Refitted on that history, the backtest gives 33 and 42 for
the same two days. The data page has the details.

With a burning season in the table, four ways of letting the season
change the model were tested against the current one by
`scripts/compare_models.py`: interactions on fire count and
eastward wind, on persistence and CAMS, all four, and a separate
burning-season fit. The bar was fixed first: clearly better in
burning season, no more than a point or two worse in calm. None
cleared it, so the model is unchanged.

## The model lab

`code/lab.py` puts the shipped model next to every alternative
worth trying, on the same days and with the same information.

- **Candidates.** Three baselines (persistence, climatology, raw
  CAMS), then CAMS rescaled by its recent ratio to the station, the
  shipped ridge, ridge with the smoke terms from week 7, ridge
  corrected by half its mean error over the last seven published
  days, analog days (the average of the most similar past days), a
  random forest, gradient boosting, a small neural network, and an
  ensemble. The first eight need nothing outside the standard
  library and could ship. The scikit-learn models are benchmarks,
  installed for the lab alone (`requirements-lab.txt`).
- **Same rules for all.** Every candidate is walked forward over the
  same days, from the same reading, and trains only on days whose
  readings had been published (`evaluate.published`). Anything that
  could ship is refitted daily, as the daily job would run it. The
  benchmarks are refitted weekly, because a daily refit of a forest
  takes minutes on its own.
- **Every reading age.** The shipped model is also scored at ages
  two to seven days, which is how the cost of a slow feed is
  measured instead of guessed.
- **Shadow forecasts.** Every morning each candidate issues its own
  forecast for tomorrow, frozen in `data/shadow.json` and scored
  when the observation lands. That builds a live record for each
  one, which no backtest can stand in for.

A challenger replaces the shipped model only if it passes all of
the rule in `lab.PROMOTION`. It must be at least 3 points of skill
better in burning season and no more than 2 points worse in calm
season. Those two thresholds were written down in week 7. It must
stay within 5% of the shipped model's error at every reading age
from two to five days. And it must do no worse over 20 live days.
Promotion is then a one-line change to `config.SHIPPED_EXTRA` in a
pull request. Nothing in the lab changes what ships.

The age test was added for a reason. Ridge with the smoke terms
clears the first two thresholds at two-day-old readings, but with
three- and four-day-old readings it breaks down early in the 2025
season. With only a handful of burning days to learn from, the
penalty chosen on a validation tail that contained none of them
came out near zero, and one forecast for a day that measured 13
came out at 2684. A rule that only looked at one age would have
shipped it.

## The likely range

Each forecast comes with a range meant to hold the measured value
four days in five. It used to be built from the spread of the fit's
own errors, which is narrower than the real spread by
construction. It held 15 of the first 27 live days.

It is now the middle 80% of the backtest's out-of-sample errors,
taken in log space and kept separate for each season
(`evaluate.calibrate`). Under a log target the range comes out
lopsided, wider above the forecast than below, which is the right
shape for a quantity that spikes upward. Its honesty is checked the
same way it is used (`evaluate.coverage`): each day's range is
sized only from the days before it.

## The outlook

Days two and three are forecast from the same station reading as
tomorrow, so the reading is a day or two older for them, and each
horizon gets a model fitted at that age. Their CAMS and weather
come from the same morning's request and are kept in
`data/outlook.json` rather than `daily.csv`, which only ever holds a
day's day-ahead forecast. In the backtest the table has only
day-ahead CAMS and weather for every horizon, which flatters days
two and three a little; their live records are the check.

## Where it stands

[Results](results.md) is regenerated every morning and is the
current evaluation, split by season, by reading age and by model,
with a live-only line.

As of late November 2026, against persistence given the same
two-day-old reading, the calm-season target is met (+13%) and
burning season is short of its 20% (about +9%): the smoky first
half of November, which the model under-forecast day after day,
pulled it down. With readings four days old, the situation the
proposal was written for, both are met (+22% in each season). The shipped ridge and its smoke-term variant have the
lowest errors of any single models on the leaderboard, ahead of
the forest, boosting and the network. The model still does not see
spikes coming. The analog list on the dashboard helps there: when
tomorrow's inputs sit closest to past days that turned out Poor, a
lower forecast deserves a second look.
