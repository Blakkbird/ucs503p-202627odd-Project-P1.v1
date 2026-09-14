# Method

## The problem, precisely

On the morning of day D-1, produce the daily mean PM2.5 at Model
Town for day D.

The word *morning* is doing real work there. It fixes what the
model is allowed to know, and that turns out to be less than the
proposal assumed.

## What is actually available at issue time

The daily job runs around 09:00 IST. The CAMS forecast for
tomorrow is available then, and so is the weather forecast. The
observations are not.

Measured on 17 August 2026, the newest observation the CPCB feed
had published was for 14 August. So on the morning of D-1, the
freshest reading is roughly D-4, not D-1. `config.OBS_LATENCY_DAYS`
holds that lag, and `features.py` refuses to read anything newer.

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
- **persistence_operational** — the freshest observation actually
  published by issue time, usually D-4. The same information set
  the model gets.

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
obviously the wrong shape. If the residuals turn out to be
strongly non-linear during the burning season, that is a finding
worth having rather than something to pre-empt with a bigger model
now.

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
  It is still computed and still published with each forecast as a
  diagnostic; it is simply not fitted on.
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

## Where it stands

Over 40 backtested days, 27 July to 11 September:

| | MAE | RMSE | band hit |
| --- | --- | --- | --- |
| model | 3.29 | 4.26 | 1.00 |
| persistence | 3.48 | 4.26 | 1.00 |
| persistence (operational) | 4.60 | 5.89 | 1.00 |
| climatology | 9.55 | 10.51 | 1.00 |
| raw CAMS | 40.96 | 43.75 | 0.00 |

Against the baseline it shares an information set with, that is a
28.3% improvement, comfortably past the 10% calm-season target.
Against the textbook baseline it is 5.2% ahead, which was not
expected and is a small enough margin to be worth rechecking on a
longer window.

The caveats have not gone away, and three are worth stating.

The window is calm season, when the observed mean sits near 23
µg/m³ and moves slowly, which is exactly the regime where
persistence is strongest and a forecast adds least. The band hit
rate is close to meaningless here: almost every day falls in Good,
so guessing Good every time would score nearly as well.

The 20% burning-season target rests on a feature that has never
fired. No training row falls in October or November, so `burning`
carries no weight yet. `fire_log` does vary and does carry weight,
which is the tested half of the mechanism.

And the feature set was chosen on this window. Each change above
has a reason that stands independently of its effect on the score,
which is why the reasons are written out rather than just the
numbers. But the reasons and the scores were looked at together,
and forty days is not enough to fully separate the two. October is
the honest test.

The live results page rebuilds from `data/metrics.json` on every
ingest, so the figures in this section are a snapshot and
[Results](results.md) is the current one.
