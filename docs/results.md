# Results

Walk-forward backtest over 2025-04-04 to 2026-11-09,
513 days. The model is refitted from scratch
before each day and only ever sees days strictly before the one
it is predicting. There is no shuffled train/test split anywhere
in this project; the rows are a time series and shuffling them
would let the model read its own future.

| Method | n | MAE | RMSE | Bias | Band correct |
| --- | ---: | ---: | ---: | ---: | ---: |
| **Pawan** | 513 | **9.23** | 14.16 | -0.17 | 74% |
| Persistence (textbook) | 477 | 7.74 | 11.50 | -0.41 | 79% |
| Persistence (operational) | 513 | 12.75 | 18.70 | +0.23 | 66% |
| Climatology | 513 | 17.59 | 22.19 | +4.21 | 35% |
| Raw CAMS | 513 | 42.16 | 50.05 | +39.74 | 13% |

## By season

The targets are set per season because the two are different
problems. Calm-season air moves slowly and persistence is hard to
beat; burning season is when a forecast is worth having.

| Season | Days | Pawan MAE | Operational persistence MAE | Skill | Target |
| --- | ---: | ---: | ---: | ---: | :--- |
| Calm (Dec to Sep) | 425 | 8.11 | 11.35 | +28.5% | 10%, met |
| Burning (Oct, Nov) | 88 | 14.65 | 19.51 | +24.9% | 20%, met |

On the **72** days whose CAMS forecast was recorded live rather than read back from an archive, Pawan's MAE is **10.09** against 12.00 for operational persistence, **+15.9%**. No archive has flattered those days, so if this figure and the totals drift apart, this is the one to believe.

## Skill

- Against operational persistence: **27.6% better** on MAE.
- Against textbook persistence: **19.3% worse** on MAE.

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
| `rh` | -0.230 |
| `cams_log` | +0.192 |
| `temp` | -0.144 |
| `obs_recent_log` | +0.127 |
| `fire_log` | +0.119 |
| `wind_speed` | -0.117 |
| `wind_u` | +0.048 |
| `burning` | +0.023 |
| `wind_v` | +0.013 |


## What is wrong with this

Worth saying plainly.

- **Burning season is a small sample.** 88 burning-season days are scored: 58 read back from archives and 30 recorded live. That is one or two seasons at most, and a dry year, a wet one or a shift in when the stubble is burnt would each move these numbers.
- **Band accuracy only means much in burning season.** On calm days almost everything falls in Good, and a method that guessed Good every time would score nearly as well.
- **Archive rows are mildly optimistic.** Rows read back from archives take CAMS and weather from series stitched out of the opening hours of successive model runs, which sit a little closer to what happened than a forecast issued a day ahead. The live-only figure, where there is one, is the check on how much that flatters the totals.
- **The feature set was chosen on calm-season data.** Every change was made for a stated reason and not only because it scored better, but the reasons and the scores were looked at together. This year's burning season, scored live as it happens, is the test nothing here was tuned against.

<small>Generated from `data/metrics.json` and `data/model.json`.</small>
