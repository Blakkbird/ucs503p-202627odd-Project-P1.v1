# Week 4 : A Job That Reported Success For Three Weeks Without Ever Working

# The Difference Between No Data Today And No Data Ever

## Error:

Two lab weeks were missed. Returning to the repository, the daily
ingest had run every morning without exception and reported
success every morning. The forecast column was current, weather
and fire counts were current, the file had grown to 115 rows.

The observation column had not moved since 14 August. Twenty-three
days, no error, no failed run, nothing in any log.

## Relevant Context

The ingest catches errors per source so that one bad endpoint
cannot take down the rest of the run, and exits non-zero only when
tomorrow's forecast is missing. Both were deliberate. Partial data
is better than none, and the job's stated purpose is producing a
forecast.

The consequence was not deliberate. An observation fetch that
failed was caught, logged into a list, and then never consulted
again by the exit code. The run went green with no ground truth
behind it, and did so every day.

The thing that gave it away was a column nobody had looked at.
`obs_hours` records how many hourly readings a daily mean is built
from. `run_daily.py` writes it on every observation it saves.
`bootstrap.py`, which seeded the history in week two, deliberately
left it blank.

```
rows in daily.csv          : 115
rows with obs_pm25         :  91
rows with obs_hours        :   0
```

Zero. Not zero since the outage — zero across the entire file. If
the daily job sets that field whenever it writes an observation,
and no row anywhere carries it, then the daily job had never
written an observation at all.

The last observation being 14 August, one day before the job first
ran, stopped looking like a coincidence. It was the boundary
between the history loaded at setup and everything the job had
failed to collect since.

## Key Observation

A third decision turned the fault permanent. The backfill window
was ten days wide. Once the gap exceeded ten days the window slid
past the hole entirely, and every subsequent run inspected only
days that were already beyond reach. The job could not have
recovered even if the underlying fault had been fixed, because it
had stopped looking at the days that were missing.

The fault itself was mundane. Two parts of the codebase asked for
the same data in two different ways:

```
scripts/bootstrap.py   ->  /v3/sensors/{id}/days    91 days returned
code/ingest/run_daily  ->  /v3/sensors/{id}/hours   nothing, ever
```

`scripts/check_sensor.py` confirmed the station was never the
problem — sensor 12235142 LIVE, 94 of the last 97 days present.
The data had been sitting there the whole time.

The API answered the `/hours` request with an empty result set and
no error. An empty result is indistinguishable from a station that
genuinely reported nothing that day, which is an ordinary thing
for a station to do. The code did the reasonable thing with a
meaningless answer.

## Solution

Three changes, addressing three different failures.

Make it loud. The job now measures how stale the freshest
observation is and fails past a limit, after saving, so a red run
still commits what it collected:

``` python
stale = obs_staleness(rows, today)
if stale is not None and stale > config.OBS_STALENESS_LIMIT_DAYS:
    print(f"ERROR: freshest observation is {stale} days old")
    ok = False
```

Make it recoverable. `BACKFILL_DAYS` went from 10 to 30, with a
test asserting the invariant that let the trap form:

``` python
assert run_daily.BACKFILL_DAYS > config.OBS_STALENESS_LIMIT_DAYS
```

Make it correct. The fetch moved to `/days`, takes the whole
window in one request rather than one per day, and the parsing was
split from the fetching so it can be exercised without a network.
The old function could only be run against the live API, which is
why no test could have caught this and none had been written.

One triggered run recovered all twenty missing days. Observations
went from 91 to 111 and the backtest window from 46 evaluation
days to 65.

**Because**

The lesson is not about the endpoint. Sending the wrong request is
an ordinary mistake and it was fixed in a few lines.

What is worth recording is that the system had no way to
distinguish *no reading published today* from *this code has never
functioned*. Both arrive as an empty list. One is routine and one
is fatal, and the ingest treated them identically for three weeks
while presenting a green check every morning.

Every individual decision that produced the blind spot was
defensible. Isolating source failures is correct. Defining success
as the forecast landing is reasonable. A bounded backfill window
is sensible. The failure was in the composition, and it was
invisible from outside because all the visible signals — green
runs, a growing file, a plausible-looking CSV — were signals about
something else.

It became findable only after the failure was made loud, and
testable only after the parsing was separated from the fetching.
The order matters: the fix for a silent failure is not primarily
the correction, it is the alarm, because without the alarm there
is nothing to tell you the correction worked.

A smaller finding fell out of the same change. With `obs_hours`
finally populating, two of the recovered days turned out to be
built from very little:

```
2026-08-28   25.1 ug/m3   from  1 hour
2026-08-29   25.5 ug/m3   from  7 hours
```

A mean over one hourly reading is not a daily mean. Nothing
filters on this yet, but the column that exposed the outage is now
also the column that will let us decide which days are trustworthy
enough to train on.
