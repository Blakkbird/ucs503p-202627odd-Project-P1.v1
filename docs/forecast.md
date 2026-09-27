# Tomorrow in Patiala

<div class="pawan-card" style="border-left-color:#5ba829">
  <div class="pawan-when">Monday 28 September</div>
  <div class="pawan-value">14<span class="pawan-unit">&micro;g/m&sup3;</span></div>
  <div class="pawan-band-name" style="color:#5ba829">Good</div>
  <div class="pawan-note">likely range 9 to 20 &middot; issued 2026-09-27</div>
</div>


<svg viewBox="0 0 760 260" class="pawan-chart" role="img" aria-label="Observed and forecast PM2.5">
<line x1="34" y1="176.0" x2="726" y2="176.0" class="pawan-grid"/>
<text x="28" y="180.0" class="pawan-axis" text-anchor="end">10</text>
<line x1="34" y1="126.0" x2="726" y2="126.0" class="pawan-grid"/>
<text x="28" y="130.0" class="pawan-axis" text-anchor="end">20</text>
<line x1="34" y1="76.0" x2="726" y2="76.0" class="pawan-grid"/>
<text x="28" y="80.0" class="pawan-axis" text-anchor="end">30</text>
<polygon points="410.1,95.5 455.2,97.8 470.3,93.7 485.3,111.8 500.3,101.3 515.4,121.5 530.4,103.2 575.6,104.1 590.6,99.5 605.7,106.2 620.7,99.2 650.8,77.4 665.8,89.0 680.9,90.6 695.9,83.5 711.0,106.0 726.0,126.0 726.0,179.2 711.0,169.4 695.9,158.3 680.9,160.8 665.8,160.0 650.8,154.2 620.7,160.6 605.7,164.3 590.6,160.7 575.6,163.3 530.4,203.1 515.4,221.5 500.3,201.2 485.3,211.4 470.3,193.3 455.2,197.4 410.1,198.2" class="pawan-band"/>
<polyline points="34.0,140.5 49.0,152.0 79.1,158.0 94.2,150.0 109.2,147.5 124.3,142.0 139.3,144.0 154.3,158.5 169.4,141.5 184.4,148.0 199.5,124.5 214.5,130.0 229.6,120.0 244.6,76.0 259.7,100.5 274.7,98.5 289.7,140.5 304.8,135.0 319.8,146.5 334.9,166.0 349.9,187.3 365.0,177.8 380.0,158.5 395.0,157.5 410.1,137.5 425.1,110.0 440.2,96.5 455.2,127.0 470.3,87.0 485.3,178.6 500.3,176.6 515.4,163.5 530.4,137.5 545.5,121.5 560.5,147.5 575.6,166.5 590.6,133.5 605.7,103.0 620.7,59.5 635.7,62.0 650.8,73.0 665.8,59.0" class="pawan-observed"/>
<polyline points="410.1,146.8 455.2,147.6 470.3,143.5 485.3,161.6 500.3,151.2 515.4,171.5 530.4,153.2 575.6,138.3 590.6,134.9 605.7,139.8 620.7,134.7 650.8,122.4 665.8,130.6 680.9,131.7 695.9,127.4 711.0,143.2 726.0,157.3" class="pawan-forecast"/>
<circle cx="410.1" cy="146.8" r="3" class="pawan-dot"/>
<circle cx="455.2" cy="147.6" r="3" class="pawan-dot"/>
<circle cx="470.3" cy="143.5" r="3" class="pawan-dot"/>
<circle cx="485.3" cy="161.6" r="3" class="pawan-dot"/>
<circle cx="500.3" cy="151.2" r="3" class="pawan-dot"/>
<circle cx="515.4" cy="171.5" r="3" class="pawan-dot"/>
<circle cx="530.4" cy="153.2" r="3" class="pawan-dot"/>
<circle cx="575.6" cy="138.3" r="3" class="pawan-dot"/>
<circle cx="590.6" cy="134.9" r="3" class="pawan-dot"/>
<circle cx="605.7" cy="139.8" r="3" class="pawan-dot"/>
<circle cx="620.7" cy="134.7" r="3" class="pawan-dot"/>
<circle cx="650.8" cy="122.4" r="3" class="pawan-dot"/>
<circle cx="665.8" cy="130.6" r="3" class="pawan-dot"/>
<circle cx="680.9" cy="131.7" r="3" class="pawan-dot"/>
<circle cx="695.9" cy="127.4" r="3" class="pawan-dot"/>
<circle cx="711.0" cy="143.2" r="3" class="pawan-dot"/>
<circle cx="726.0" cy="157.3" r="3" class="pawan-dot"/>
<text x="34.0" y="252" class="pawan-axis" text-anchor="middle">13 Aug</text>
<text x="726.0" y="252" class="pawan-axis" text-anchor="middle">28 Sep</text>
</svg>

The solid line is what the station at Model Town measured. The
dotted line is what Pawan said the day before, and the shaded
area is the range it gave. Observations arrive about three days
behind, so the most recent forecasts have nothing to sit against
yet.

## How it has done so far

Since the service started issuing forecasts it has made **17** of them, **13** of which have an observation to be checked against. On those, the mean absolute error is **6.5 &micro;g/m&sup3;** and the AQI band was right **10 times out of 13**.


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

<small>Generated from `data/predictions.json` at 2026-09-27T13:58:31+05:30.</small>
