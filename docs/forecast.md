# Tomorrow in Patiala

<div class="pawan-card" style="border-left-color:#5ba829">
  <div class="pawan-when">Wednesday 23 September</div>
  <div class="pawan-value">21<span class="pawan-unit">&micro;g/m&sup3;</span></div>
  <div class="pawan-band-name" style="color:#5ba829">Good</div>
  <div class="pawan-note">likely range 14 to 30 &middot; issued 2026-09-22</div>
</div>


<svg viewBox="0 0 760 260" class="pawan-chart" role="img" aria-label="Observed and forecast PM2.5">
<line x1="34" y1="175.9" x2="726" y2="175.9" class="pawan-grid"/>
<text x="28" y="179.9" class="pawan-axis" text-anchor="end">10</text>
<line x1="34" y1="125.7" x2="726" y2="125.7" class="pawan-grid"/>
<text x="28" y="129.7" class="pawan-axis" text-anchor="end">20</text>
<line x1="34" y1="75.6" x2="726" y2="75.6" class="pawan-grid"/>
<text x="28" y="79.6" class="pawan-axis" text-anchor="end">30</text>
<polygon points="485.3,95.1 530.4,97.4 545.5,93.3 560.5,111.4 575.6,100.9 590.6,121.2 605.7,102.8 650.8,103.7 665.8,99.1 680.9,105.9 695.9,98.9 726.0,77.0 726.0,154.0 695.9,160.4 680.9,164.1 665.8,160.5 650.8,163.1 605.7,203.0 590.6,221.5 575.6,201.1 560.5,211.4 545.5,193.2 530.4,197.3 485.3,198.1" class="pawan-band"/>
<polyline points="34.0,123.7 49.0,166.3 64.1,148.3 79.1,153.3 94.2,155.3 109.2,140.3 124.3,151.8 154.3,157.8 169.4,149.8 184.4,147.3 199.5,141.8 214.5,143.8 229.6,158.3 244.6,141.3 259.7,147.8 274.7,124.2 289.7,129.7 304.8,119.7 319.8,75.6 334.9,100.2 349.9,98.2 365.0,140.3 380.0,134.8 395.0,146.3 410.1,165.8 425.1,187.2 440.2,177.6 455.2,158.3 470.3,157.3 485.3,137.3 500.3,109.7 515.4,96.1 530.4,126.7 545.5,86.6 560.5,178.5 575.6,176.5 590.6,163.3 605.7,137.3 620.7,121.2 635.7,147.3 650.8,166.3 665.8,133.2 680.9,102.7 695.9,59.0" class="pawan-observed"/>
<polyline points="485.3,146.6 530.4,147.4 545.5,143.3 560.5,161.4 575.6,151.0 590.6,171.4 605.7,153.0 650.8,138.1 665.8,134.6 680.9,139.6 695.9,134.4 726.0,122.1" class="pawan-forecast"/>
<circle cx="485.3" cy="146.6" r="3" class="pawan-dot"/>
<circle cx="530.4" cy="147.4" r="3" class="pawan-dot"/>
<circle cx="545.5" cy="143.3" r="3" class="pawan-dot"/>
<circle cx="560.5" cy="161.4" r="3" class="pawan-dot"/>
<circle cx="575.6" cy="151.0" r="3" class="pawan-dot"/>
<circle cx="590.6" cy="171.4" r="3" class="pawan-dot"/>
<circle cx="605.7" cy="153.0" r="3" class="pawan-dot"/>
<circle cx="650.8" cy="138.1" r="3" class="pawan-dot"/>
<circle cx="665.8" cy="134.6" r="3" class="pawan-dot"/>
<circle cx="680.9" cy="139.6" r="3" class="pawan-dot"/>
<circle cx="695.9" cy="134.4" r="3" class="pawan-dot"/>
<circle cx="726.0" cy="122.1" r="3" class="pawan-dot"/>
<text x="34.0" y="252" class="pawan-axis" text-anchor="middle">08 Aug</text>
<text x="726.0" y="252" class="pawan-axis" text-anchor="middle">23 Sep</text>
</svg>

The solid line is what the station at Model Town measured. The
dotted line is what Pawan said the day before, and the shaded
area is the range it gave. Observations arrive about three days
behind, so the most recent forecasts have nothing to sit against
yet.

## How it has done so far

Since the service started issuing forecasts it has made **12** of them, **11** of which have an observation to be checked against. On those, the mean absolute error is **5.5 &micro;g/m&sup3;** and the AQI band was right **10 times out of 11**.


That is the live record, not the backtest. It is short, and it
only covers a quiet time of year. [The full evaluation](results.md)
is the number to argue with.

| Day | Forecast | Observed | Error | Band |
| --- | ---: | ---: | ---: | :--- |
| 2026-09-21 | 18.3 | 33.3 | -15.0 | Good (missed) |
| 2026-09-20 | 17.2 | 24.6 | -7.4 | Good (correct) |
| 2026-09-19 | 18.2 | 18.5 | -0.3 | Good (correct) |
| 2026-09-18 | 17.5 | 11.9 | +5.6 | Good (correct) |
| 2026-09-15 | 14.6 | 17.7 | -3.1 | Good (correct) |
| 2026-09-14 | 10.9 | 12.5 | -1.6 | Good (correct) |
| 2026-09-13 | 15.0 | 9.9 | +5.1 | Good (correct) |
| 2026-09-12 | 12.9 | 9.5 | +3.4 | Good (correct) |
| 2026-09-11 | 16.5 | 27.8 | -11.3 | Good (correct) |
| 2026-09-10 | 15.7 | 19.8 | -4.1 | Good (correct) |


A forecast is written once and never revised. When the
observation for that day finally publishes it is filed beside the
original, untouched. Rewriting yesterday's forecast after
yesterday happened is the easiest way to build a system that
looks far better than it is.

<small>Generated from `data/predictions.json` at 2026-09-22T13:23:36+05:30.</small>
