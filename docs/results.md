# Results

Walk-forward backtest over 2026-07-27 to 2026-09-17,
46 days. The model is refitted from scratch
before each day and only ever sees days strictly before the one
it is predicting. There is no shuffled train/test split anywhere
in this project; the rows are a time series and shuffling them
would let the model read its own future.

| Method | n | MAE | RMSE | Bias | Band correct |
| --- | ---: | ---: | ---: | ---: | ---: |
| **Pawan** | 46 | **3.40** | 4.30 | -0.06 | 100% |
| Persistence (textbook) | 45 | 3.79 | 4.98 | -0.29 | 100% |
| Persistence (operational) | 46 | 5.40 | 6.84 | -0.69 | 100% |
| Climatology | 46 | 9.41 | 10.38 | +9.07 | 100% |
| Raw CAMS | 46 | 38.93 | 41.88 | +38.93 | 2% |

## Skill

- Against operational persistence: **36.9% better** on MAE.
- Against textbook persistence: **10.1% better** on MAE.

The two baselines are both persistence, and the difference
between them is the whole argument.

**Operational persistence** is the best a person could do at
08:00 using what the CPCB feed has actually published by then,
which is a reading about four days old. That is the same
information Pawan has, so it is a fair comparison, and it is what
the forecast is worth to somebody deciding whether to run
outside tomorrow.

**Textbook persistence** uses yesterday's reading. Nobody has
yesterday's reading when the forecast goes out. It is reported
because it is the figure quoted in the proposal, and because it
marks the ceiling: the gap between the two baselines is the cost
of the publication lag, and closing it needs a faster feed rather
than a better model.

## What the model weighs

Fitted on 40+ rows, in log space,
with the penalty chosen inside each fit on a held-out tail.
Weights are on standardised inputs, so their sizes can be
compared with each other but not read as physics.

| Feature | Weight |
| --- | ---: |
| `cams_log` | +0.144 |
| `temp` | +0.086 |
| `fire_log` | +0.050 |
| `wind_u` | +0.042 |
| `obs_recent_log` | +0.038 |
| `rh` | -0.036 |
| `wind_v` | -0.025 |
| `wind_speed` | +0.023 |
| `burning` | +0.000 |


## What is wrong with this

Worth saying plainly, because all of it will matter by November.

- **The window is short and quiet.** Every scored day is calm
  season. The band accuracy in particular is close to meaningless
  here, because almost every day falls in Good and a method that
  guessed Good every time would score nearly as well.
- **`burning` has never fired.** No training row falls in October
  or November, so the burning-season flag carries no weight yet
  and the 20% target for that season rests on a feature the model
  has not seen. `fire_log` does vary and does carry weight, which
  is the part of the mechanism that has been tested.
- **Meteorology starts late.** Open-Meteo's archive reaches back
  about 92 days, so the earliest rows have no weather and drop
  out of the fit. The usable set grows by one row a day.
- **The feature set was chosen on this window.** Every change was
  made for a stated reason and not only because it scored better,
  but the reasons and the scores were looked at together, and a
  40-day window is not enough to separate the two. The honest
  test is how this holds up in October, on days nothing here has
  been tuned against.

<small>Generated from `data/metrics.json` and `data/model.json`.</small>
