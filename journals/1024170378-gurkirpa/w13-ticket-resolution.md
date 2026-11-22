# Week 13 : An Endpoint That Would Answer Anything

# Six Times The Record, Waved Through

## Error:

The dashboard's sliders let a reader change tomorrow's inputs and
watch the forecast move. The new API does the same for programs:
`POST /whatif` runs the shipped model on whatever readings it is
sent.

Given 16 November's real inputs, it returned exactly the forecast
the daily job had issued: 52.53 µg/m³, Satisfactory, likely 34 to
91. The trouble showed up when it was given inputs far outside
anything seen before. It answered every one, and the first guard
written against that let the worst of them through:

```
request                       answer        flagged
fires 20000                   70.5 Moderate (nothing)
reading 2000, cams 2000,
  fires 20000, no wind        1111 Severe   cams, reading
```

The most fires ever seen upwind in one day is 3147. A request for
20,000 got a confident Moderate and no warning.

## Relevant Context

+  A linear model has no ceiling. It keeps extrapolating in a straight
   line long after the physics has stopped agreeing. Week 7's smoke
   variant once forecast 2684 for a day that measured 13.
+  The first guard flagged any input more than four standard
   deviations from its mean in the training rows. It checked the
   model's own inputs, the values after `features.transform()`.
+  Fires enter the model as `log(1 + count)`. log(1 + 20000) is 9.9,
   and log(1 + 3147) is 8.1. On that scale six times the record is a
   modest step, well inside four standard deviations.

## Key Observation

The log is right for the model: smoke does not double each time the
fire count doubles. It is the wrong scale for asking whether the
model has seen anything like this before. That question is about the
readings, in their own units, and needs the range of the rows the
model was fitted on, which the model file did not keep.

## Solution

+  `evaluate.save_model()` now stores the lowest and highest value of
   every reading in the fitted rows, in `model.json` next to the
   weights. Wind direction is left out, since every bearing turns up
   in a year.
+  `/whatif` flags any reading outside that range and reports the
   range with it:

```
"extrapolating": [{"input": "fires", "value": 20000,
                   "fitted_low": 0, "fitted_high": 3147}]
```

+  Impossible inputs are refused before the model sees them. Pydantic
   field limits return a 422 for humidity over 100%, a negative fire
   count, or a bearing outside 0 to 360.
+  The rest of the API is read-only and serves the same files as the
   site. `/forecast` returns tomorrow, its range and advice, and the
   two days after, or the reason there is no forecast. `/forecasts`
   returns the whole record with outcomes, `/models` the leaderboard,
   and `/health` the age of the newest reading. FastAPI builds the
   interactive docs at `/docs` from the type annotations.
+  Each request reads the files fresh, so the API never needs
   restarting when the daily job runs. If a request lands while a
   file is half rewritten, it gets a 503 saying which file, never
   half an answer.

The test suite went from 191 to 203. The API's tests write their own
data files, so they do not depend on what the daily job committed
that morning.

**Because**

An endpoint that runs a model is a promise that the number means
something. When the inputs leave the ground the model was fitted
on, the honest answer is the number plus a warning that it is
guesswork. A guard has to look at the inputs on the same scale as
the question it is answering.
