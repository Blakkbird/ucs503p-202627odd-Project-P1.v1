# Week 12 : Two Ways To Miss A Forecast

# A Weather Service That Said "Not Now"

## Error:

From 15 to 21 November, five of the seven scheduled runs went red,
and four days got no forecast at all. Each time the station reading
and the fire count came in fine and the weather request failed:

```
15 Nov  forecast 2026-11-16: HTTP 429 for https://api.open-meteo.com/v1/forecast?...
16 Nov  forecast 2026-11-17: unreachable after 3 tries: The handshake operation timed out
17 Nov  forecast 2026-11-18: unreachable after 3 tries: The handshake operation timed out
19 Nov  forecast 2026-11-20: unreachable after 3 tries: The handshake operation timed out
21 Nov  forecast 2026-11-22: unreachable after 3 tries: The handshake operation timed out
```

The 15th was saved by a manual run four and a half hours later,
which went through without a problem.

## Relevant Context

+  HTTP 429 means "too many requests". Open-Meteo is free and limits
   how often one IP address may call it. GitHub's runners share their
   addresses with other people's jobs, so the quota can be used up
   before this job has asked for anything.
+  `fetch()` retried server faults (5xx) but treated every 4xx as
   permanent, since a bad key or a bad URL will not fix itself. 429
   fell into that group.
+  Timeouts were retried, but after waits of 2 and 4 seconds. A
   connection that cannot complete a TLS handshake rarely recovers
   in six seconds.
+  The job is scheduled for 08:00 IST, but GitHub has been starting
   it seven to eight hours late. There was no second attempt in the
   day.

## Key Observation

Both failures clear with time, and with a different machine. 429
means "come back shortly", and a stalled handshake usually means a
busy route from one runner's address. The manual run on the 15th,
from a fresh runner hours later, needed nothing else.

So one attempt a day was the real weak point: any failure, however
brief its cause, cost that day's forecast.

## Solution

+  `fetch()` now retries a 429 and a stalled connection after 15 and
   then 30 seconds, or after the `Retry-After` time if the source
   gives one, capped at a minute. Other 4xx errors still fail at once.
+  Four backup runs through the day. A small first job (`code/due.py`)
   decides whether a backup has anything to do. It works only if
   today's run has already gone out without a forecast, or if it is
   evening and today's run has left no trace at all. Otherwise it
   stops within seconds and makes no commit.
+  A backup never runs ahead of the morning run. GitHub's delays vary,
   and a backup that happened to fire on time could otherwise issue
   tomorrow's forecast before the morning run, from a reading a day
   staler.

# Twelve Days Of Smoke

## Error:

From 4 to 14 November the station read between 60 and 114 µg/m³,
mostly above 75. With the week 9 fix, the shipped model said 55 to
75, low on all but one day:

```
day       measured   shipped
6 Nov     91.8       60.1
8 Nov     114.0      56.5
9 Nov     106.0      57.2
12 Nov    106.0      68.9
```

Over the twelve November days in the backtest its error was 30.0,
against 26.6 for persistence.

## Relevant Context

The signal was there. Fires were at their highest of the season,
several hundred detections a day upwind and 539 on 8 November. CAMS
read between 60 and 99, close to what the station measured.

But CAMS usually overshoots this station several times over. In
the second half of October it read 76 to 122 while the station
measured 16 to 79. The model has learnt to pull CAMS down hard, and
in a week when CAMS happened to be about right, that correction is
what dragged the forecast low. The fire count did push the forecast
up, but its weight was fitted mostly on days with far fewer fires.

## Key Observation

The errors had the same sign day after day. The model cannot tell
from one day's inputs that this is the week CAMS is right. It can
tell that it has been too low all week, and its own recent errors
are the cheapest signal that a spell like this is on.

## Solution

+  A new challenger in the model lab, `RecentError`. It shifts the
   shipped ridge's forecast by half its mean log error over the last
   seven published days. Those errors are measured out of sample: a
   ridge fitted without those seven days is asked about them. It
   uses half the error rather than all of it, because spells end and
   a full correction keeps pushing for days after they do.
+  On the lab's backtest it is the best single model:

```
                      MAE    calm     burning   Nov 2026
shipped ridge         9.16   +13.2%   +11.6%    30.0
ridge + recent error  8.95   +15.4%   +13.3%    25.0
persistence          10.50                      26.6
```

+  It is not promoted. Across both burning seasons its gain is 1.7
   points of skill, and the rule asks for 3. The seven days and the
   half were also picked from five variants on this same backtest,
   which flatters them. It now issues a shadow forecast every
   morning, and its live record decides.

The test suite went from 175 to 191.

**Because**

Both misses had the same shape: a system that gave up after one
try. The fetch gave up on a source that only wanted a minute's
wait. The model gave up on a week of evidence that it was running
low. Each now gets a second look, and neither is allowed to hide a
real failure.
