# Results

Walk-forward backtest over 2025-04-04 to 2026-11-01,
507 days. The model is refitted from scratch
before each day and only ever sees days strictly before the one
it is predicting. There is no shuffled train/test split anywhere
in this project; the rows are a time series and shuffling them
would let the model read its own future.

| Method | n | MAE | RMSE | Bias | Band correct |
| --- | ---: | ---: | ---: | ---: | ---: |
| **Pawan** | 507 | **8.85** | 13.39 | +0.32 | 75% |
| Persistence (textbook) | 472 | 7.70 | 11.45 | -0.40 | 79% |
| Persistence (operational) | 507 | 12.60 | 18.38 | +0.45 | 66% |
| Climatology | 507 | 17.09 | 21.31 | +4.97 | 35% |
| Raw CAMS | 507 | 42.40 | 50.25 | +40.37 | 13% |

## By season

The targets are set per season because the two are different
problems. Calm-season air moves slowly and persistence is hard to
beat; burning season is when a forecast is worth having.

| Season | Days | Pawan MAE | Operational persistence MAE | Skill | Target |
| --- | ---: | ---: | ---: | ---: | :--- |
| Calm (Dec to Sep) | 425 | 8.11 | 11.35 | +28.5% | 10%, met |
| Burning (Oct, Nov) | 82 | 12.68 | 19.07 | +33.5% | 20%, met |

On the **66** days whose CAMS forecast was recorded live rather than read back from an archive, Pawan's MAE is **7.24** against 10.76 for operational persistence, **+32.8%**. No archive has flattered those days, so if this figure and the totals drift apart, this is the one to believe.

## Skill

- Against operational persistence: **29.8% better** on MAE.
- Against textbook persistence: **14.9% worse** on MAE.

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
| `rh` | -0.245 |
| `cams_log` | +0.197 |
| `temp` | -0.152 |
| `obs_recent_log` | +0.118 |
| `wind_speed` | -0.118 |
| `fire_log` | +0.113 |
| `wind_u` | +0.049 |
| `wind_v` | +0.019 |
| `burning` | +0.011 |


## What is wrong with this

Worth saying plainly.

- **Burning season is a small sample.** 82 burning-season days are scored: 58 read back from archives and 24 recorded live. That is one or two seasons at most, and a dry year, a wet one or a shift in when the stubble is burnt would each move these numbers.
- **Band accuracy only means much in burning season.** On calm days almost everything falls in Good, and a method that guessed Good every time would score nearly as well.
- **Archive rows are mildly optimistic.** Rows read back from archives take CAMS and weather from series stitched out of the opening hours of successive model runs, which sit a little closer to what happened than a forecast issued a day ahead. The live-only figure, where there is one, is the check on how much that flatters the totals.
- **The feature set was chosen on calm-season data.** Every change was made for a stated reason and not only because it scored better, but the reasons and the scores were looked at together. This year's burning season, scored live as it happens, is the test nothing here was tuned against.

<small>Generated from `data/metrics.json` and `data/model.json`.</small>
