# Results

Walk-forward backtest over 2025-04-03 to 2026-11-15,
482 days. The model is refitted from scratch
before each day and only ever sees days strictly before the one
it is predicting. Every row uses the station reading from 2 days before the day being forecast, which is the freshest the feed now publishes in time. There is no shuffled train/test split
anywhere in this project; the rows are a time series and shuffling
them would let the model read its own future.

| Method | n | MAE | RMSE | Bias | Band correct |
| --- | ---: | ---: | ---: | ---: | ---: |
| **Pawan** | 482 | **9.22** | 14.50 | -0.35 | 74% |
| Persistence (textbook) | 457 | 8.17 | 12.43 | -0.28 | 78% |
| Persistence (operational) | 482 | 10.53 | 16.22 | -0.35 | 71% |
| Climatology | 482 | 18.30 | 23.12 | +3.22 | 33% |
| Raw CAMS | 482 | 41.66 | 49.70 | +38.78 | 14% |

## By season

The targets are set per season because the two are different
problems. Calm-season air moves slowly and persistence is hard to
beat; burning season is when a forecast is worth having.

| Season | Days | Pawan MAE | Operational persistence MAE | Skill | Target |
| --- | ---: | ---: | ---: | ---: | :--- |
| Calm (Dec to Sep) | 394 | 7.98 | 9.19 | +13.2% | 10%, met |
| Burning (Oct, Nov) | 88 | 14.78 | 16.49 | +10.4% | 20%, not met |

On the **72** days whose CAMS forecast was recorded live rather than read back from an archive, Pawan's MAE is **10.60** against 10.96 for operational persistence, **+3.3%**. No archive has flattered those days, so if this figure and the totals drift apart, this is the one to believe.

## Skill

- Against operational persistence: **12.4% better** on MAE.
- Against textbook persistence: **12.9% worse** on MAE.

The two baselines are both persistence, and the difference
between them is the whole argument.

**Operational persistence** repeats the freshest reading the CPCB
feed had published when the forecast went out, two days old at the
reference age. That is the same information Pawan has, so it is a
fair comparison, and it is what the forecast is worth to somebody
deciding whether to run outside tomorrow.

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
| `obs_recent_log` | +0.195 |
| `rh` | -0.191 |
| `cams_log` | +0.167 |
| `temp` | -0.125 |
| `wind_speed` | -0.107 |
| `fire_log` | +0.106 |
| `wind_u` | +0.040 |
| `burning` | +0.037 |
| `wind_v` | +0.003 |


## How old the reading is

The forecast uses the freshest station reading on file, with a
model fitted at exactly that reading's age. The lab scores the
shipped model at every age against persistence given the same
reading. An older reading is a weaker forecast on its own, so the
model's skill over it grows, while the weight the model puts on it
shrinks.

| Reading age | Days | Pawan MAE | Persistence MAE | Skill | Calm | Burning | Weight on the reading |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2 days | 481 | 9.16 | 10.50 | +12.8% | +13.2% | +11.6% | +0.193 |
| 3 days | 471 | 9.58 | 11.55 | +17.0% | +15.9% | +19.6% | +0.165 |
| 4 days | 469 | 9.91 | 12.64 | +21.5% | +21.6% | +21.5% | +0.140 |
| 5 days | 466 | 10.00 | 13.10 | +23.7% | +23.3% | +24.7% | +0.108 |
| 6 days | 463 | 10.13 | 13.40 | +24.4% | +24.6% | +23.9% | +0.089 |
| 7 days | 461 | 10.50 | 13.99 | +24.9% | +27.1% | +18.6% | +0.061 |

## Model comparison

Every candidate is scored on the same 481 days with
the same information: the reading the shipped forecast had, and
training rows only from days already published. Models that could
ship are refitted daily, as the daily job would run them; the
scikit-learn benchmarks weekly. Live MAE comes from the shadow
forecasts every model issues each morning, with the number of
scored days in brackets.

| Model | Kind | MAE | Skill | Calm | Burning | Live MAE | Verdict |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| Ridge + smoke terms | linear | 8.96 | +14.7% | +13.4% | +17.9% | - | Breaks down with 4-day-old readings |
| **Ridge regression (shipped)** | linear | **9.16** | +12.8% | +13.2% | +11.6% | - | Shipped |
| Ensemble | ensemble | 9.22 | +12.2% | +13.1% | +9.8% | - | Benchmark: needs scikit-learn |
| Random forest | tree | 9.63 | +8.2% | +11.3% | +0.5% | - | Benchmark: needs scikit-learn |
| Analog days | analog | 9.98 | +4.9% | +8.2% | -3.5% | - | Not clearly better in burning season |
| Gradient boosting | tree | 10.35 | +1.4% | +3.1% | -2.8% | - | Benchmark: needs scikit-learn |
| Neural network | neural | 10.39 | +1.1% | -0.2% | +4.3% | - | Benchmark: needs scikit-learn |
| Persistence | baseline | 10.50 | +0.0% | +0.0% | +0.0% | - | Baseline |
| CAMS rescaled | linear | 13.67 | -30.2% | -24.2% | -45.3% | - | Not clearly better in burning season |
| Climatology | baseline | 18.45 | -75.7% | -78.8% | -67.9% | - | Baseline |
| Raw CAMS | baseline | 41.69 | -297.0% | -378.8% | -89.6% | - | Baseline |

A challenger replaces the shipped model only when it is at least
3 points of skill better in
burning season, no more than 2
points worse in calm season, within
5% of the shipped model's error
at every reading age from two to five days, and no worse over
20 live days. The first two thresholds were
written down in week 7, before any candidate was scored against
them. The age test was added when the smoke terms passed at two
days and broke down at four.

## Three-day outlook

Days two and three come from the same reading as tomorrow, so it is
a day or two older relative to them, and each horizon has its own
model fitted at that age.

| Days ahead | Reading age | Days | Pawan MAE | Persistence MAE | Skill | Range held |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 2 days | 482 | 9.22 | 10.53 | +12.4% | 363 of 452 |
| 2 | 3 days | 472 | 9.67 | 11.57 | +16.5% | 355 of 442 |
| 3 | 4 days | 470 | 10.07 | 12.63 | +20.3% | 359 of 440 |

## Likely range

The likely range is the middle 80% of the backtest's own errors, taken out of sample and per season, so four days in five should land inside it. Sized only from the days before it, the range held the measured value on **363 of 452** backtest days (80%), and on 62 of 88 in burning season (70%), where the first days of a season have the fewest errors to size from.

## Limitations

What the figures above do not show.

- **Burning season is a small sample.** 88 burning-season days are scored: 55 read back from archives and 33 recorded live. That is one or two seasons at most, and a dry year, a wet one or a shift in when the stubble is burnt would each move these numbers.
- **Band accuracy only means much in burning season.** On calm days almost everything falls in Good, and a method that guessed Good every time would score nearly as well.
- **Archive rows are mildly optimistic.** Rows read back from archives take CAMS and weather from series stitched out of the opening hours of successive model runs, which sit a little closer to what happened than a forecast issued a day ahead. The live-only figure, where there is one, is the check on how much that flatters the totals.
- **The feature set was chosen on calm-season data.** Every change was made for a stated reason and not only because it scored better, but the reasons and the scores were looked at together. This year's burning season, scored live as it happens, is the test nothing here was tuned against.
- **The outlook's backtest is a little kind.** The table keeps one CAMS and weather forecast per day, the day-ahead one, so days two and three are backtested with inputs better than they will have live. Their reading and fire count are moved back properly, which is the larger effect.

<small>Generated from `data/metrics.json`, `data/model.json` and
`data/leaderboard.json`.</small>
