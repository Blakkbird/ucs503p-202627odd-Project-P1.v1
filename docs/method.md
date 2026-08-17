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

## Where it stands

The harness runs end to end. On the record available in mid
August, over 46 backtested days:

| | MAE | RMSE | band hit |
| --- | --- | --- | --- |
| model | 7.27 | 9.03 | 0.83 |
| persistence | 6.12 | 8.45 | 0.85 |
| persistence (operational) | 8.76 | 11.77 | 0.74 |
| climatology | 11.74 | 12.70 | 0.78 |
| raw CAMS | 42.35 | 47.28 | 0.11 |

So: the model beats the baseline it shares an information set with
by about 17%, and loses to the textbook baseline by about 19%.
Both facts are real and neither cancels the other.

Two things are worth saying plainly about this. The window is
monsoon, when the observed mean sits near 25 µg/m³ and moves
slowly, which is exactly the regime where persistence is strongest
and a forecast adds least. And the meteorology columns are not in
this fit at all — they were blank for most of the history until
the backfill, so the run above uses CAMS, lagged observations and
seasonality only. The features most likely to matter in October,
wind and fire counts, have not been tested yet.

Reaching the proposal's targets against textbook persistence, on
this information set, may not be possible. That is better known in
August than in November, and it is the reason the backtest was
built before the model rather than after it.
