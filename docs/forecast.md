# Tomorrow in Patiala

<div class="pawan-card" style="border-left-color:#5ba829">
  <div class="pawan-when">Friday 18 September</div>
  <div class="pawan-value">18<span class="pawan-unit">&micro;g/m&sup3;</span></div>
  <div class="pawan-band-name" style="color:#5ba829">Good</div>
  <div class="pawan-note">likely range 13 to 24 &middot; issued 2026-09-17</div>
</div>


<svg viewBox="0 0 760 260" class="pawan-chart" role="img" aria-label="Observed and forecast PM2.5">
<line x1="34" y1="170.3" x2="726" y2="170.3" class="pawan-grid"/>
<text x="28" y="174.3" class="pawan-axis" text-anchor="end">10</text>
<line x1="34" y1="114.7" x2="726" y2="114.7" class="pawan-grid"/>
<text x="28" y="118.7" class="pawan-axis" text-anchor="end">20</text>
<line x1="34" y1="59.0" x2="726" y2="59.0" class="pawan-grid"/>
<text x="28" y="63.0" class="pawan-axis" text-anchor="end">30</text>
<polygon points="560.5,80.7 605.7,83.3 620.7,78.7 635.7,98.8 650.8,87.1 665.8,109.7 680.9,89.3 726.0,90.3 726.0,156.2 680.9,200.5 665.8,221.0 650.8,198.4 635.7,209.7 620.7,189.6 605.7,194.2 560.5,195.0" class="pawan-band"/>
<polyline points="34.0,148.1 49.0,185.0 64.1,155.9 79.1,126.9 94.2,167.6 109.2,112.5 124.3,159.8 139.3,139.7 154.3,145.3 169.4,147.5 184.4,130.8 199.5,143.6 229.6,150.3 244.6,141.4 259.7,138.6 274.7,132.5 289.7,134.7 304.8,150.9 319.8,131.9 334.9,139.2 349.9,113.0 365.0,119.1 380.0,108.0 395.0,59.0 410.1,86.3 425.1,84.1 440.2,130.8 455.2,124.7 470.3,137.5 485.3,159.2 500.3,182.9 515.4,172.3 530.4,150.9 545.5,149.8 560.5,127.5 575.6,96.9 590.6,81.9 605.7,115.8 620.7,71.3 635.7,173.2 650.8,171.0 665.8,156.4 680.9,127.5 695.9,109.7" class="pawan-observed"/>
<polyline points="560.5,137.8 605.7,138.7 620.7,134.2 635.7,154.3 650.8,142.7 665.8,165.3 680.9,144.9 726.0,128.4" class="pawan-forecast"/>
<circle cx="560.5" cy="137.8" r="3" class="pawan-dot"/>
<circle cx="605.7" cy="138.7" r="3" class="pawan-dot"/>
<circle cx="620.7" cy="134.2" r="3" class="pawan-dot"/>
<circle cx="635.7" cy="154.3" r="3" class="pawan-dot"/>
<circle cx="650.8" cy="142.7" r="3" class="pawan-dot"/>
<circle cx="665.8" cy="165.3" r="3" class="pawan-dot"/>
<circle cx="680.9" cy="144.9" r="3" class="pawan-dot"/>
<circle cx="726.0" cy="128.4" r="3" class="pawan-dot"/>
<text x="34.0" y="252" class="pawan-axis" text-anchor="middle">03 Aug</text>
<text x="726.0" y="252" class="pawan-axis" text-anchor="middle">18 Sep</text>
</svg>

The solid line is what the station at Model Town measured. The
dotted line is what Pawan said the day before, and the shaded
area is the range it gave. Observations arrive about three days
behind, so the most recent forecasts have nothing to sit against
yet.

## How it has done so far

Since the service started issuing forecasts it has made **8** of them, **7** of which have an observation to be checked against. On those, the mean absolute error is **4.6 &micro;g/m&sup3;** and the AQI band was right **7 times out of 7**.


That is the live record, not the backtest. It is short, and it
only covers a quiet time of year. [The full evaluation](results.md)
is the number to argue with.

| Day | Forecast | Observed | Error | Band |
| --- | ---: | ---: | ---: | :--- |
| 2026-09-15 | 14.6 | 17.7 | -3.1 | Good (correct) |
| 2026-09-14 | 10.9 | 12.5 | -1.6 | Good (correct) |
| 2026-09-13 | 15.0 | 9.9 | +5.1 | Good (correct) |
| 2026-09-12 | 12.9 | 9.5 | +3.4 | Good (correct) |
| 2026-09-11 | 16.5 | 27.8 | -11.3 | Good (correct) |
| 2026-09-10 | 15.7 | 19.8 | -4.1 | Good (correct) |
| 2026-09-07 | 15.8 | 19.4 | -3.6 | Good (correct) |


A forecast is written once and never revised. When the
observation for that day finally publishes it is filed beside the
original, untouched. Rewriting yesterday's forecast after
yesterday happened is the easiest way to build a system that
looks far better than it is.

<small>Generated from `data/predictions.json` at 2026-09-17T13:25:43+05:30.</small>
