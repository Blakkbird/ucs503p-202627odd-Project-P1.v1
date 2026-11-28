# Results

Walk-forward backtest over 2025-04-03 to 2026-11-27,
490 days. The model is refitted from scratch
before each day and only ever sees days strictly before the one
it is predicting. Every row uses the station reading from 2 days before the day being forecast, which is the freshest the feed now publishes in time. There is no shuffled train/test split
anywhere in this project; the rows are a time series and shuffling
them would let the model read its own future.

| Method | n | MAE | RMSE | Bias | Band correct |
| --- | ---: | ---: | ---: | ---: | ---: |
| **Pawan** | 490 | **9.27** | 14.48 | -0.32 | 74% |
| Persistence (textbook) | 465 | 8.25 | 12.52 | -0.22 | 77% |
| Persistence (operational) | 490 | 10.53 | 16.17 | -0.33 | 71% |
| Climatology | 490 | 18.39 | 23.18 | +2.77 | 34% |
| Raw CAMS | 490 | 41.52 | 49.60 | +38.68 | 14% |

## By season

The targets are set per season because the two are different
problems. Calm-season air moves slowly and persistence is hard to
beat; burning season is when a forecast is worth having.

| Season | Days | Pawan MAE | Operational persistence MAE | Skill | Target |
| --- | ---: | ---: | ---: | ---: | :--- |
| Calm (Dec to Sep) | 394 | 7.98 | 9.19 | +13.2% | 10%, met |
| Burning (Oct, Nov) | 96 | 14.58 | 16.00 | +8.9% | 20%, not met |

On the **80** days whose CAMS forecast was recorded live rather than read back from an archive, Pawan's MAE is **10.78** against 10.92 for operational persistence, **+1.3%**. No archive has flattered those days, so if this figure and the totals drift apart, this is the one to believe.

## Skill

- Against operational persistence: **11.9% better** on MAE.
- Against textbook persistence: **12.3% worse** on MAE.

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
| `obs_recent_log` | +0.196 |
| `rh` | -0.172 |
| `cams_log` | +0.161 |
| `temp` | -0.113 |
| `fire_log` | +0.109 |
| `wind_speed` | -0.097 |
| `wind_u` | +0.043 |
| `burning` | +0.037 |
| `wind_v` | -0.005 |


## How old the reading is

The forecast uses the freshest station reading on file, with a
model fitted at exactly that reading's age. The lab scores the
shipped model at every age against persistence given the same
reading. An older reading is a weaker forecast on its own, so the
model's skill over it grows, while the weight the model puts on it
shrinks.

| Reading age | Days | Pawan MAE | Persistence MAE | Skill | Calm | Burning | Weight on the reading |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2 days | 485 | 9.22 | 10.53 | +12.5% | +13.2% | +10.7% | +0.195 |
| 3 days | 475 | 9.61 | 11.53 | +16.7% | +15.9% | +18.5% | +0.168 |
| 4 days | 473 | 9.99 | 12.77 | +21.7% | +21.6% | +22.2% | +0.146 |
| 5 days | 470 | 10.04 | 13.11 | +23.4% | +23.3% | +23.6% | +0.112 |
| 6 days | 467 | 10.18 | 13.52 | +24.7% | +24.6% | +25.2% | +0.105 |
| 7 days | 465 | 10.55 | 14.22 | +25.8% | +27.1% | +22.3% | +0.065 |

## Model comparison

Every candidate is scored on the same 485 days with
the same information: the reading the shipped forecast had, and
training rows only from days already published. Models that could
ship are refitted daily, as the daily job would run them; the
scikit-learn benchmarks weekly. Live MAE comes from the shadow
forecasts every model issues each morning, with the number of
scored days in brackets.

| Model | Kind | MAE | Skill | Calm | Burning | Live MAE | Verdict |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| Ridge + recent error | linear | 9.03 | +14.2% | +15.4% | +11.5% | 14.96 (5) | Not clearly better in burning season |
| Ridge + smoke terms | linear | 9.04 | +14.2% | +13.4% | +16.1% | 13.14 (8) | Breaks down with 4-day-old readings |
| **Ridge regression (shipped)** | linear | **9.22** | +12.5% | +13.2% | +10.7% | 12.35 (8) | Shipped |
| Ensemble | ensemble | 9.30 | +11.8% | +13.1% | +8.4% | 12.76 (8) | Benchmark: needs scikit-learn |
| Random forest | tree | 9.69 | +8.0% | +11.3% | -0.1% | 12.38 (8) | Benchmark: needs scikit-learn |
| Analog days | analog | 10.08 | +4.3% | +8.2% | -5.2% | 12.62 (8) | Not clearly better in burning season |
| Gradient boosting | tree | 10.41 | +1.1% | +3.1% | -3.6% | 15.44 (8) | Benchmark: needs scikit-learn |
| Neural network | neural | 10.46 | +0.7% | -0.2% | +2.9% | 12.96 (8) | Benchmark: needs scikit-learn |
| Persistence | baseline | 10.53 | +0.0% | +0.0% | +0.0% | 10.56 (8) | Baseline |
| CAMS rescaled | linear | 13.81 | -31.1% | -24.2% | -47.8% | 21.96 (8) | Not clearly better in burning season |
| Climatology | baseline | 18.48 | -75.5% | -78.8% | -67.3% | 24.05 (8) | Baseline |
| Raw CAMS | baseline | 41.59 | -294.8% | -378.8% | -90.2% | 33.19 (8) | Baseline |

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
| 1 | 2 days | 490 | 9.27 | 10.53 | +11.9% | 371 of 460 |
| 2 | 3 days | 480 | 9.68 | 11.51 | +16.0% | 363 of 450 |
| 3 | 4 days | 478 | 10.10 | 12.76 | +20.8% | 367 of 448 |

## Likely range

The likely range is the middle 80% of the backtest's own errors, taken out of sample and per season, so four days in five should land inside it. Sized only from the days before it, the range held the measured value on **371 of 460** backtest days (81%), and on 70 of 96 in burning season (73%), where the first days of a season have the fewest errors to size from.

## Limitations

What the figures above do not show.

- **Burning season is a small sample.** 96 burning-season days are scored: 55 read back from archives and 41 recorded live. That is one or two seasons at most, and a dry year, a wet one or a shift in when the stubble is burnt would each move these numbers.
- **Band accuracy only means much in burning season.** On calm days almost everything falls in Good, and a method that guessed Good every time would score nearly as well.
- **Archive rows are mildly optimistic.** Rows read back from archives take CAMS and weather from series stitched out of the opening hours of successive model runs, which sit a little closer to what happened than a forecast issued a day ahead. The live-only figure, where there is one, is the check on how much that flatters the totals.
- **The feature set was chosen on calm-season data.** Every change was made for a stated reason and not only because it scored better, but the reasons and the scores were looked at together. This year's burning season, scored live as it happens, is the test nothing here was tuned against.
- **The outlook's backtest is a little kind.** The table keeps one CAMS and weather forecast per day, the day-ahead one, so days two and three are backtested with inputs better than they will have live. Their reading and fire count are moved back properly, which is the larger effect.

<small>Generated from `data/metrics.json`, `data/model.json` and
`data/leaderboard.json`.</small>
