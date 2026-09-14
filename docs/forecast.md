# Tomorrow in Patiala

<div class="pawan-card" style="border-left-color:#5ba829">
  <div class="pawan-when">Tuesday 15 September</div>
  <div class="pawan-value">15<span class="pawan-unit">&micro;g/m&sup3;</span></div>
  <div class="pawan-band-name" style="color:#5ba829">Good</div>
  <div class="pawan-note">likely range 5 to 25 &middot; issued 2026-09-14</div>
</div>


<svg viewBox="0 0 760 260" class="pawan-chart" role="img" aria-label="Observed and forecast PM2.5">
<line x1="34" y1="170.3" x2="726" y2="170.3" class="pawan-grid"/>
<text x="28" y="174.3" class="pawan-axis" text-anchor="end">10</text>
<line x1="34" y1="114.7" x2="726" y2="114.7" class="pawan-grid"/>
<text x="28" y="118.7" class="pawan-axis" text-anchor="end">20</text>
<line x1="34" y1="59.0" x2="726" y2="59.0" class="pawan-grid"/>
<text x="28" y="63.0" class="pawan-axis" text-anchor="end">30</text>
<polygon points="605.7,80.7 650.8,83.3 665.8,78.7 680.9,98.8 695.9,87.1 711.0,109.7 726.0,89.3 726.0,200.5 711.0,221.0 695.9,198.4 680.9,209.7 665.8,189.6 650.8,194.2 605.7,195.0" class="pawan-band"/>
<polyline points="34.0,186.7 49.0,162.6 64.1,161.4 79.1,148.1 94.2,185.0 109.2,155.9 124.3,126.9 139.3,167.6 154.3,112.5 169.4,159.8 184.4,139.7 199.5,145.3 214.5,147.5 229.6,130.8 244.6,143.6 274.7,150.3 289.7,141.4 304.8,138.6 319.8,132.5 334.9,134.7 349.9,150.9 365.0,131.9 380.0,139.2 395.0,113.0 410.1,119.1 425.1,108.0 440.2,59.0 455.2,86.3 470.3,84.1 485.3,130.8 500.3,124.7 515.4,137.5 530.4,159.2 545.5,182.9 560.5,172.3 575.6,150.9 590.6,149.8 605.7,127.5 620.7,96.9 635.7,81.9 650.8,115.8 665.8,71.3" class="pawan-observed"/>
<polyline points="605.7,137.8 650.8,138.7 665.8,134.2 680.9,154.3 695.9,142.7 711.0,165.3 726.0,144.9" class="pawan-forecast"/>
<circle cx="605.7" cy="137.8" r="3" class="pawan-dot"/>
<circle cx="650.8" cy="138.7" r="3" class="pawan-dot"/>
<circle cx="665.8" cy="134.2" r="3" class="pawan-dot"/>
<circle cx="680.9" cy="154.3" r="3" class="pawan-dot"/>
<circle cx="695.9" cy="142.7" r="3" class="pawan-dot"/>
<circle cx="711.0" cy="165.3" r="3" class="pawan-dot"/>
<circle cx="726.0" cy="144.9" r="3" class="pawan-dot"/>
<text x="34.0" y="252" class="pawan-axis" text-anchor="middle">31 Jul</text>
<text x="726.0" y="252" class="pawan-axis" text-anchor="middle">15 Sep</text>
</svg>

The solid line is what the station at Model Town measured. The
dotted line is what Pawan said the day before, and the shaded
area is the range it gave. Observations arrive about three days
behind, so the most recent forecasts have nothing to sit against
yet.

## How it has done so far

Since the service started issuing forecasts it has made **7** of them, **3** of which have an observation to be checked against. On those, the mean absolute error is **6.3 &micro;g/m&sup3;** and the AQI band was right **3 times out of 3**.


That is the live record, not the backtest. It is short, and it
only covers a quiet time of year. [The full evaluation](results.md)
is the number to argue with.

| Day | Forecast | Observed | Error | Band |
| --- | ---: | ---: | ---: | :--- |
| 2026-09-11 | 16.5 | 27.8 | -11.3 | Good (correct) |
| 2026-09-10 | 15.7 | 19.8 | -4.1 | Good (correct) |
| 2026-09-07 | 15.8 | 19.4 | -3.6 | Good (correct) |


A forecast is written once and never revised. When the
observation for that day finally publishes it is filed beside the
original, untouched. Rewriting yesterday's forecast after
yesterday happened is the easiest way to build a system that
looks far better than it is.

<small>Generated from `data/predictions.json` at 2026-09-14T21:38:57+05:30.</small>
