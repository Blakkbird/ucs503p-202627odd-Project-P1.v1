# Week 2 : A Filtered Query That Returned Everything

# Silently Dropped Query Parameters, and a Retired Sensor

## Error:

Week two was group formation and the practice pitch. Alongside
that we verified the data sources before committing to the idea.

The Patiala station exposes two PM2.5 sensors. To choose between
them I asked each for its daily values over the last 97 days.
The counts came back impossible:

```
sensor 15243     : 1000 rows   last seen 2022-10-31
sensor 12235142  :  531 rows   last seen 2026-08-15
```

A 97 day window cannot contain 1000 daily rows. Worse, my
selection logic ranked by row count and recommended `15243`, a
sensor that had not reported in almost four years.

## Relevant Context

The query was:

``` python
url = (f"https://api.openaq.org/v3/sensors/{sensor_id}/days?"
       + urllib.parse.urlencode({
           "datetime_from": start.isoformat(),
           "datetime_to": end.isoformat(),
           "limit": 1000}))
```

1000 is exactly the `limit`. 531 is roughly the full history of
the second sensor. Both are the entire series, truncated.

## Key Observation

Two separate faults, and the second was mine.

+  The v3 aggregate endpoints take **`date_from`** and
   **`date_to`**. The names I used were not recognised, and the
   API discarded them instead of rejecting the request. It then
   returned the whole series and reported success.
+  My ranking treated recency as a tiebreak rather than a filter,
   so more history beat still working.

The general rule worth keeping: **when a filtered query returns
exactly your limit, the filter did not apply.**

The same wrong names were in the daily ingest job, where the
window is a single day and the limit is small. There the failure
would have been worse and silent: the API would have returned the
oldest rows in the series, and the job would have recorded 2018
readings as yesterday's observation.

## Solution

Correct the parameter names, and stop trusting the server to have
honoured them:

``` python
params = {"date_from": start.isoformat(),
          "date_to": end.isoformat(), "limit": 1000, "page": page}
...
kept = [r for r in results
        if start.isoformat() <= day_of(r) <= end.isoformat()]
```

The client-side filter is not redundant. It converts a silent
wrong answer into an empty one, and the ingest job already fails
its run when nothing is written.

Selection now excludes any sensor quiet for more than 14 days
before ranking. Rerun:

```
15243      0 days in window   [STALE, excluded]
12235142  96 days in window   <-- use this one
```

The choice is pinned in `code/config.py` with the retired id kept
alongside it, so nobody silently reverses it later.

**Because**

An API that ignores unknown parameters cannot be trusted to
enforce a filter, so the filter has to be enforced twice. A
response that is well formed, returns HTTP 200, and contains
plausible values can still be the wrong data entirely, which
means validating status codes is not validating data.

The ranking bug is the more useful lesson. The heuristic was
reasonable and the output was confidently wrong, and only the
impossible row count exposed it. A number that cannot be true is
worth more than a number that merely looks odd.
