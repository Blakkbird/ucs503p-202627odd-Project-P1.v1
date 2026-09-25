# Tomorrow in Patiala

<div class="pawan-card" style="border-left-color:#5ba829">
  <div class="pawan-when">Saturday 26 September</div>
  <div class="pawan-value">20<span class="pawan-unit">&micro;g/m&sup3;</span></div>
  <div class="pawan-band-name" style="color:#5ba829">Good</div>
  <div class="pawan-note">likely range 14 to 28 &middot; issued 2026-09-25</div>
</div>


<svg viewBox="0 0 760 260" class="pawan-chart" role="img" aria-label="Observed and forecast PM2.5">
<line x1="34" y1="176.0" x2="726" y2="176.0" class="pawan-grid"/>
<text x="28" y="180.0" class="pawan-axis" text-anchor="end">10</text>
<line x1="34" y1="126.0" x2="726" y2="126.0" class="pawan-grid"/>
<text x="28" y="130.0" class="pawan-axis" text-anchor="end">20</text>
<line x1="34" y1="76.0" x2="726" y2="76.0" class="pawan-grid"/>
<text x="28" y="80.0" class="pawan-axis" text-anchor="end">30</text>
<polygon points="440.2,95.5 485.3,97.8 500.3,93.7 515.4,111.8 530.4,101.3 545.5,121.5 560.5,103.2 605.7,104.1 620.7,99.5 635.7,106.2 650.8,99.2 680.9,77.4 695.9,89.0 711.0,90.6 726.0,83.5 726.0,158.3 711.0,160.8 695.9,160.0 680.9,154.2 650.8,160.6 635.7,164.3 620.7,160.7 605.7,163.3 560.5,203.1 545.5,221.5 530.4,201.2 515.4,211.4 500.3,193.3 485.3,197.4 440.2,198.2" class="pawan-band"/>
<polyline points="34.0,153.5 49.0,155.5 64.1,140.5 79.1,152.0 109.2,158.0 124.3,150.0 139.3,147.5 154.3,142.0 169.4,144.0 184.4,158.5 199.5,141.5 214.5,148.0 229.6,124.5 244.6,130.0 259.7,120.0 274.7,76.0 289.7,100.5 304.8,98.5 319.8,140.5 334.9,135.0 349.9,146.5 365.0,166.0 380.0,187.3 395.0,177.8 410.1,158.5 425.1,157.5 440.2,137.5 455.2,110.0 470.3,96.5 485.3,127.0 500.3,87.0 515.4,178.6 530.4,176.6 545.5,163.5 560.5,137.5 575.6,121.5 590.6,147.5 605.7,166.5 620.7,133.5 635.7,103.0 650.8,59.5 665.8,62.0 680.9,73.0 695.9,59.0" class="pawan-observed"/>
<polyline points="440.2,146.8 485.3,147.6 500.3,143.5 515.4,161.6 530.4,151.2 545.5,171.5 560.5,153.2 605.7,138.3 620.7,134.9 635.7,139.8 650.8,134.7 680.9,122.4 695.9,130.6 711.0,131.7 726.0,127.4" class="pawan-forecast"/>
<circle cx="440.2" cy="146.8" r="3" class="pawan-dot"/>
<circle cx="485.3" cy="147.6" r="3" class="pawan-dot"/>
<circle cx="500.3" cy="143.5" r="3" class="pawan-dot"/>
<circle cx="515.4" cy="161.6" r="3" class="pawan-dot"/>
<circle cx="530.4" cy="151.2" r="3" class="pawan-dot"/>
<circle cx="545.5" cy="171.5" r="3" class="pawan-dot"/>
<circle cx="560.5" cy="153.2" r="3" class="pawan-dot"/>
<circle cx="605.7" cy="138.3" r="3" class="pawan-dot"/>
<circle cx="620.7" cy="134.9" r="3" class="pawan-dot"/>
<circle cx="635.7" cy="139.8" r="3" class="pawan-dot"/>
<circle cx="650.8" cy="134.7" r="3" class="pawan-dot"/>
<circle cx="680.9" cy="122.4" r="3" class="pawan-dot"/>
<circle cx="695.9" cy="130.6" r="3" class="pawan-dot"/>
<circle cx="711.0" cy="131.7" r="3" class="pawan-dot"/>
<circle cx="726.0" cy="127.4" r="3" class="pawan-dot"/>
<text x="34.0" y="252" class="pawan-axis" text-anchor="middle">11 Aug</text>
<text x="726.0" y="252" class="pawan-axis" text-anchor="middle">26 Sep</text>
</svg>

The solid line is what the station at Model Town measured. The
dotted line is what Pawan said the day before, and the shaded
area is the range it gave. Observations arrive about three days
behind, so the most recent forecasts have nothing to sit against
yet.

## How it has done so far

Since the service started issuing forecasts it has made **15** of them, **13** of which have an observation to be checked against. On those, the mean absolute error is **6.5 &micro;g/m&sup3;** and the AQI band was right **10 times out of 13**.


That is the live record, not the backtest. It is short, and it
only covers a quiet time of year. [The full evaluation](results.md)
is the number to argue with.

| Day | Forecast | Observed | Error | Band |
| --- | ---: | ---: | ---: | :--- |
| 2026-09-24 | 19.1 | 33.4 | -14.3 | Good (missed) |
| 2026-09-23 | 20.7 | 30.6 | -9.9 | Good (missed) |
| 2026-09-21 | 18.3 | 33.3 | -15.0 | Good (missed) |
| 2026-09-20 | 17.2 | 24.6 | -7.4 | Good (correct) |
| 2026-09-19 | 18.2 | 18.5 | -0.3 | Good (correct) |
| 2026-09-18 | 17.5 | 11.9 | +5.6 | Good (correct) |
| 2026-09-15 | 14.6 | 17.7 | -3.1 | Good (correct) |
| 2026-09-14 | 10.9 | 12.5 | -1.6 | Good (correct) |
| 2026-09-13 | 15.0 | 9.9 | +5.1 | Good (correct) |
| 2026-09-12 | 12.9 | 9.5 | +3.4 | Good (correct) |


A forecast is written once and never revised. When the
observation for that day finally publishes it is filed beside the
original, untouched. Rewriting yesterday's forecast after
yesterday happened is the easiest way to build a system that
looks far better than it is.

<small>Generated from `data/predictions.json` at 2026-09-25T13:36:02+05:30.</small>
