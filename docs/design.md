# Design

How Pawan is put together: what it was required to do, the parts
that do it, how data moves between them, and where each requirement
is tested. The diagrams are drawn from the code as it stands; the
numbers that change daily live on [Results](results.md).

## Requirements

### Functional

| ID | The system shall | Where | Status |
| --- | --- | --- | --- |
| FR1 | Collect each day's station reading, the CAMS and weather forecasts, and upwind fire detections | `ingest/run_daily.py` | Met, daily since August 2026 |
| FR2 | Issue a next-day PM2.5 forecast every day without anyone running it | `predict.py`, Daily ingest workflow | Met |
| FR3 | Freeze each forecast when issued, and score it when the station's reading for that day is published | `predict.py` | Met |
| FR4 | Show the forecast, its likely range, what drove it and the track record on a public page | `pages.py`, `docs/dashboard/` | Met |
| FR5 | Compare candidate models on the same days, and keep a live record for each | `candidates.py`, `lab.py` | Met, twelve models |
| FR6 | Forecast two and three days ahead | `predict.py` | Met |
| FR7 | Post each day's forecast to a Telegram channel | `notify.py` | Met; needs the two secrets set |
| FR8 | Serve the forecasts, the leaderboard and a what-if over HTTP | `api.py` | Met, runs locally |
| FR9 | Recover the same day from a failed or late run | `due.py`, `fetch()` retries | Met |

### Non-functional

| ID | Requirement | How it is met | Status |
| --- | --- | --- | --- |
| NFR1 | Accuracy: reduce error against persistence by 10% in calm season and 20% in burning season | Ridge in log space, local readings, fires and weather | Calm met at every reading age. Burning met with the three- and four-day-old readings the target was set for, below it with two-day-old ones |
| NFR2 | Honesty: no forecast or backtest uses data published after its issue time | Fixed reading ages; training cut at the last published day | Met, tested |
| NFR3 | Reliability: one failed step never loses the day's data | Steps that cannot block the commit; backup runs; retries | Met |
| NFR4 | Maintainability: the forecast path cannot break on a dependency upgrade | Forecast is standard library only; extras pinned and optional | Met |
| NFR5 | Security: no key ever reaches the repository or a public log | Secrets in GitHub; URLs redacted before quoting | Met, tested |
| NFR6 | Transparency: every number on the site is regenerated from the data each day | `pages.py` writes the pages from `data/` | Met |
| NFR7 | Usability: the site works on a phone, with no server to keep alive | Static pages; layout checked at 390 px | Met |

## Use cases

```mermaid
flowchart LR
    reader([Reader])
    client([Program using the API])
    dev([Maintainer])
    sched([GitHub scheduler])
    subgraph pawan [Pawan]
        uc1(View tomorrow's forecast and range)
        uc2(Try other inputs on the dashboard)
        uc3(Compare the models)
        uc4(Receive the daily post)
        uc5(Query forecasts or a what-if over HTTP)
        uc6(Run the daily pipeline)
        uc7(Score earlier forecasts)
        uc8(Promote a challenger)
    end
    reader --- uc1
    reader --- uc2
    reader --- uc3
    reader --- uc4
    client --- uc5
    sched --- uc6
    uc6 -. includes .-> uc7
    dev --- uc6
    dev --- uc8
```

Promoting a challenger is deliberately a person's job. The lab says
when a model passes the rule; a maintainer makes the one-line change
in a pull request.

## Context

```mermaid
flowchart LR
    openaq[OpenAQ<br/>CPCB station 5544]
    meteo[Open-Meteo<br/>CAMS and weather]
    firms[NASA FIRMS<br/>fire detections]
    pawan((Pawan))
    readers[Readers]
    tg[Telegram channel]
    clients[API clients]
    openaq -- daily PM2.5 --> pawan
    meteo -- three-day forecasts --> pawan
    firms -- fire positions --> pawan
    pawan -- dashboard and pages --> readers
    pawan -- daily post --> tg
    pawan -- JSON --> clients
    clients -- what-if inputs --> pawan
```

## Data flow

Processes are numbered in the order the daily job runs them. Every
store is a file in the repository, so its history is the commit log.

```mermaid
flowchart TB
    openaq[OpenAQ]
    meteo[Open-Meteo]
    firms[NASA FIRMS]
    p1((1 Ingest))
    p2((2 Fit and backtest))
    p3((3 Issue forecasts))
    p4((4 Model lab))
    p5((5 Notify))
    p6((6 Build pages))
    p7((7 API))
    d1[(D1 daily.csv<br/>outlook.json, fires.json)]
    d2[(D2 model.json<br/>metrics.json)]
    d3[(D3 predictions.json)]
    d4[(D4 leaderboard.json<br/>shadow.json)]
    d5[(D5 site pages<br/>dashboard data.json)]
    tg[Telegram]
    readers[Readers]
    clients[API clients]
    openaq --> p1
    meteo --> p1
    firms --> p1
    p1 --> d1
    d1 --> p2 --> d2
    d1 --> p3
    d2 --> p3
    p3 --> d3
    d1 --> p4 --> d4
    d3 --> p5 --> tg
    d1 --> p6
    d3 --> p6
    d4 --> p6
    p6 --> d5 --> readers
    d2 --> p7
    d3 --> p7
    d4 --> p7
    p7 --> clients
```

## The daily run

```mermaid
sequenceDiagram
    autonumber
    participant S as GitHub scheduler
    participant W as Workflow
    participant Due as due.py
    participant Ing as run_daily.py
    participant Src as OpenAQ, Open-Meteo, FIRMS
    participant Mod as evaluate, predict, lab
    participant N as notify.py
    participant Tg as Telegram
    participant Pg as pages.py
    participant R as Repository
    participant Site as GitHub Pages
    S->>W: start (08:00 IST, or a backup later)
    W->>Due: anything to do?
    Due->>R: read predictions.json
    alt backup run, and today's run issued a forecast or has not run yet
        Due-->>W: no
    else morning run, or today's run left no forecast
        Due-->>W: yes
        W->>Ing: fetch
        Ing->>Src: readings, forecasts, fires
        Src-->>Ing: data (a busy source is retried)
        Ing->>R: daily.csv, outlook.json, fires.json
        W->>Mod: refit, forecast, lab
        Mod->>R: model, metrics, frozen forecasts, leaderboard
        W->>N: post
        N->>Tg: tomorrow's forecast, once
        W->>Pg: build
        Pg->>R: pages and dashboard data
        W->>W: run the test suite
        W->>R: commit and push
        R->>Site: deploy
    end
```

Each step after the fetch runs even if an earlier one failed, and
the run only turns red after the commit, so a bad morning still
keeps whatever data it did collect.

## A forecast's life

```mermaid
stateDiagram-v2
    [*] --> Pending: tomorrow becomes the target
    Pending --> Skipped: inputs missing, or no reading within 7 days
    Pending --> Issued: inputs complete
    Issued --> Scored: station publishes the day (16 hours or more)
    Issued --> Unscored: the day's reading is too thin to count
    Scored --> [*]
    Unscored --> [*]
    Skipped --> [*]
    note right of Issued
        frozen: a rerun never changes it
    end note
```

The forecast is made by a model fitted at exactly the age of the
freshest reading on file, and the age is recorded with it.

## Main classes

```mermaid
classDiagram
    class Sample {
        date day
        list x
        float y
        float persistence_op
        float obs_age
        int horizon
        dict raw
        complete() bool
        usable() bool
    }
    class Ridge {
        float alpha
        list coef
        list means
        list devs
        fit(x, y)
        predict_one(row) float
        to_dict() dict
    }
    class Candidate {
        <<abstract>>
        str key
        bool shippable
        bool sklearn
        int refit_every
        fit(train) Fitted
    }
    class Fitted {
        predict(sample) float
        predict_many(samples) list
    }
    Candidate <|-- Persistence
    Candidate <|-- Climatology
    Candidate <|-- RawCams
    Candidate <|-- CamsRescale
    Candidate <|-- RidgeModel
    Candidate <|-- RecentError
    Candidate <|-- Analogs
    Candidate <|-- SklearnModel
    SklearnModel <|-- RandomForest
    SklearnModel <|-- GradientBoosting
    SklearnModel <|-- NeuralNet
    Candidate <|-- Ensemble
    Candidate ..> Fitted : returns
    Candidate ..> Sample : trains on
    RidgeModel ..> Ridge : fits
    RecentError ..> Ridge : fits
```

`features.build()` turns `daily.csv` into `Sample` rows at a stated
reading age. `evaluate.fit()` chooses the ridge penalty by
validation on the most recent rows and returns a `Ridge`. The model
lab calls every `Candidate` through the same `fit()`, so all of them
are scored on the same days.

## Data model

```mermaid
erDiagram
    DAILY_ROW {
        date date PK
        float obs_pm25
        int obs_hours
        float cams_pm25
        date cams_issue_date
        float temp_mean
        float rh_mean
        float wind_speed_mean
        float wind_dir_mean
        int fire_count
        datetime ingested_at
    }
    FORECAST {
        date date PK
        int horizon PK
        date issued
        datetime issued_at
        float pm25
        string band
        float range_low
        float range_high
        float actual
        float error
    }
    SHADOW_FORECAST {
        date date PK
        string model PK
        float pm25
        float actual
    }
    MODEL_FILE {
        float alpha
        int obs_age
        string features
        string ranges
    }
    DAILY_ROW ||--o{ FORECAST : "is scored against"
    DAILY_ROW ||--o{ SHADOW_FORECAST : "is scored against"
    MODEL_FILE ||--o{ FORECAST : "issues"
```

`daily.csv` is the only store of observations; every other file is
derived from it and can be rebuilt. [Data](data.md) describes each
column and file.

## Deployment

```mermaid
flowchart TB
    subgraph gh [GitHub]
        repo[(Repository<br/>code, data, docs)]
        subgraph runner [Actions runner: Ubuntu 24.04, Python 3.12]
            wf[Daily ingest workflow]
            ci[CI: ruff and pytest]
        end
        pages[GitHub Pages<br/>MkDocs site and dashboard]
    end
    subgraph ext [Public data services]
        openaq[OpenAQ v3]
        meteo[Open-Meteo]
        firms[NASA FIRMS]
    end
    tg[Telegram Bot API]
    browser[Reader's browser]
    phone[Telegram app]
    subgraph local [Developer machine]
        api[FastAPI and uvicorn<br/>code/api.py]
    end
    wf -->|HTTPS| openaq
    wf -->|HTTPS| meteo
    wf -->|HTTPS| firms
    wf -->|commit| repo
    repo -->|every push| ci
    repo -->|mkdocs gh-deploy| pages
    wf -->|HTTPS| tg --> phone
    pages -->|HTTPS| browser
    repo -->|clone| api
```

There is no server to keep running. The pipeline lives on GitHub's
runners, the site is static files, and the API is optional and runs
wherever it is cloned.

## Design decisions

| Decision | Instead of | Why |
| --- | --- | --- |
| CSV committed to git | A database | One file of a few hundred rows; the commit log is a free audit trail of every change to the data |
| Static site, separate optional API | A web app with a server | Nothing to keep alive; the dashboard cannot go down with a server |
| Forecast path in the standard library | scikit-learn throughout | The daily job runs unattended for months; the less it depends on, the less can change underneath it |
| Ridge regression in log space | Trees or a neural network | Beats them on about 500 days of data, in the lab's own comparison; its arithmetic can be shown exactly on the dashboard |
| One model per reading age | One model, whatever the reading's age | A model fitted on two-day-old readings would weigh a five-day-old one wrongly |
| Forecasts frozen when issued | Recomputed as the model improves | The track record is of what was actually claimed |
| A written promotion rule | Shipping whichever model scores best | A model can win one exam by luck; the rule asks for several |

## Testing

All tests run on every pull request and every data commit. The
table maps each test file to the requirements it protects.

| Test file | Tests | Covers |
| --- | ---: | --- |
| `test_pages.py` | 32 | FR4, NFR6: pages, dashboard data, the breakdown matching the forecast |
| `test_ingest.py` | 29 | FR1, FR9, NFR5: parsing, wind averaging, retries, key redaction |
| `test_features.py` | 27 | NFR2: reading ages, thin days, the fire lag |
| `test_model.py` | 20 | FR3, NFR2: ridge, the backtest's training cut, the likely range |
| `test_lab.py` | 21 | FR5: fair walk-forward, the promotion rule, shadow forecasts |
| `test_history.py` | 18 | FR1: the one-off history extension |
| `test_predict.py` | 16 | FR2, FR3, FR6: freezing, scoring, the outlook |
| `test_notify.py` | 13 | FR7, NFR5: the post, posting once, the token never printed |
| `test_api.py` | 12 | FR8: every endpoint, what-if parity, input checks |
| `test_schema.py` | 7 | NFR2, NFR5: the data file's columns, no keys in the code, no future data in training rows |
| `test_due.py` | 8 | FR9: when a backup run works and when it stands down |
| **Total** | **203** | |

Beyond unit tests, the walk-forward backtest is the system test of
the forecast: it replays every day since April 2025 with only what
was known at the time. The live record, scored daily, is the
acceptance test.
