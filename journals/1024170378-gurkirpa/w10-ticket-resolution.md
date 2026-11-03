# Week 10 : Eleven Models, One Exam

# A Promotion Rule That Only Looked At One Age

## Error:

The first run of the model lab put ridge with the smoke terms at
the top of the leaderboard. The smoke terms let the fire count and
the westerly wind count for more in burning season. Against the
rule written down in week 7, it passed: clearly better in burning
season, no worse in calm.

```
                         MAE    calm     burning
shipped ridge            8.76   +13.2%   +18.9%
ridge + smoke terms      8.67   +13.4%   +22.1%
```

By that rule it should have shipped. The same model, scored with
older station readings, said otherwise:

```
reading age   shipped ridge   ridge + smoke terms
2 days        8.76            8.67
3 days        9.13            10.65
4 days        9.43            15.50
```

The worst single day was 8 October 2025. The station measured
13.3 µg/m³. The smoke model forecast 2684.

## Relevant Context

After the prototype review, the direction was more models with
published comparisons. The week 7 script compared four variants of
one ridge model at one reading age, and it trained each backtest
step on days whose readings had not been published yet. Week 9
fixed that leak in the main backtest.

The feed's speed decides which reading age the forecast actually
gets on a given morning (week 9). A model that only works at one
age only works when the feed is on time.

## Key Observation

The blow-up came from the penalty search. Early in October 2025
the training set held only a few burning-season days, and the
validation tail used to choose the penalty held none at all. On
that tail the smoke terms were zero, so any penalty looked as good
as any other, and the search picked almost none. The first real
burning days then met weights that had never been held in check.

The lab's first version refitted every model weekly, to keep the
tree models fast. That happened to skip those days. The daily job
refits every morning, so a candidate that could ship has to be
tested the way it would actually run.

## Solution

+  `code/candidates.py`: eleven candidates behind one interface.
   Three baselines; CAMS rescaled; the shipped ridge; ridge with
   smoke terms; analog days, which average the most similar past
   days; a random forest, gradient boosting and a small neural
   network from scikit-learn; and an ensemble. The standard-library
   ones could ship. The scikit-learn ones are benchmarks, imported
   only inside their fits.
+  `code/lab.py` walks every candidate forward over the same days,
   with training cut at the last published reading. Anything that
   could ship is refitted daily and the benchmarks weekly. The
   shipped model is also scored at every reading age from two to
   seven days.
+  The promotion rule is written in code (`lab.PROMOTION`) and
   printed on the results page. The week 7 thresholds come first.
   Then the challenger must stay within 5% of the shipped model's
   error at every age from two to five days, and do no worse over
   20 days of live forecasts. Promotion itself is a one-line change
   to `config.SHIPPED_EXTRA`, made in a pull request.
+  Every model now issues a shadow forecast each morning,
   frozen in `data/shadow.json`, so each one builds a live record
   alongside the real forecast.
+  The likely range is now the middle 80% of the backtest's own
   out-of-sample errors, per season, instead of the fit's in-sample
   spread. Sized only from earlier days, it held 355 of 440 backtest
   days (81%), and 54 of 76 in burning season (71%), where a new
   season starts with the fewest errors to size from.
+  A three-day outlook: days two and three from the same reading,
   each with a model fitted at that reading's age, frozen like
   tomorrow's forecast.
+  The dashboard gained the outlook, a "days like tomorrow" list,
   the leaderboard with what every model says about tomorrow, a
   chart of error against reading age, and the range's hit rate.

The leaderboard now reads:

```
model                       MAE     burning   standing
ridge + smoke terms         8.67    +22.1%    breaks down at 4-day readings
ridge (shipped)             8.76    +18.9%    shipped
ensemble                    8.90    +14.1%    benchmark
random forest               9.30     +3.8%    benchmark
analog days                 9.76     -4.8%    not better in burning season
gradient boosting          10.03     -0.0%    benchmark
neural network             10.04     +9.7%    benchmark
persistence                10.27              baseline
```

On about five hundred rows the regularised linear model beats the
forest, the boosting and the network. That is a result worth
having, not a reason to stop looking: the lab reruns every week,
and the shadow forecasts score every model live through the rest
of this burning season.

The test suite went from 128 to 161.

**Because**

A lab is not there to find a winner. It is there to stop a lucky
one. The smoke terms were better on the one exam they had been
set, and the rule that would have promoted them was honest about
everything except how many exams there are.
