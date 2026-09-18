# Tomorrow in Patiala

<div class="pawan-card" style="border-left-color:#5ba829">
  <div class="pawan-when">Saturday 19 September</div>
  <div class="pawan-value">18<span class="pawan-unit">&micro;g/m&sup3;</span></div>
  <div class="pawan-band-name" style="color:#5ba829">Good</div>
  <div class="pawan-note">likely range 13 to 25 &middot; issued 2026-09-18</div>
</div>


<svg viewBox="0 0 760 260" class="pawan-chart" role="img" aria-label="Observed and forecast PM2.5">
<line x1="34" y1="170.3" x2="726" y2="170.3" class="pawan-grid"/>
<text x="28" y="174.3" class="pawan-axis" text-anchor="end">10</text>
<line x1="34" y1="114.7" x2="726" y2="114.7" class="pawan-grid"/>
<text x="28" y="118.7" class="pawan-axis" text-anchor="end">20</text>
<line x1="34" y1="59.0" x2="726" y2="59.0" class="pawan-grid"/>
<text x="28" y="63.0" class="pawan-axis" text-anchor="end">30</text>
<polygon points="545.5,80.7 590.6,83.3 605.7,78.7 620.7,98.8 635.7,87.1 650.8,109.7 665.8,89.3 711.0,90.3 726.0,85.1 726.0,153.3 711.0,156.2 665.8,200.5 650.8,221.0 635.7,198.4 620.7,209.7 605.7,189.6 590.6,194.2 545.5,195.0" class="pawan-band"/>
<polyline points="34.0,185.0 49.0,155.9 64.1,126.9 79.1,167.6 94.2,112.5 109.2,159.8 124.3,139.7 139.3,145.3 154.3,147.5 169.4,130.8 184.4,143.6 214.5,150.3 229.6,141.4 244.6,138.6 259.7,132.5 274.7,134.7 289.7,150.9 304.8,131.9 319.8,139.2 334.9,113.0 349.9,119.1 365.0,108.0 380.0,59.0 395.0,86.3 410.1,84.1 425.1,130.8 440.2,124.7 455.2,137.5 470.3,159.2 485.3,182.9 500.3,172.3 515.4,150.9 530.4,149.8 545.5,127.5 560.5,96.9 575.6,81.9 590.6,115.8 605.7,71.3 620.7,173.2 635.7,171.0 650.8,156.4 665.8,127.5 680.9,109.7 695.9,138.6" class="pawan-observed"/>
<polyline points="545.5,137.8 590.6,138.7 605.7,134.2 620.7,154.3 635.7,142.7 650.8,165.3 665.8,144.9 711.0,128.4 726.0,124.5" class="pawan-forecast"/>
<circle cx="545.5" cy="137.8" r="3" class="pawan-dot"/>
<circle cx="590.6" cy="138.7" r="3" class="pawan-dot"/>
<circle cx="605.7" cy="134.2" r="3" class="pawan-dot"/>
<circle cx="620.7" cy="154.3" r="3" class="pawan-dot"/>
<circle cx="635.7" cy="142.7" r="3" class="pawan-dot"/>
<circle cx="650.8" cy="165.3" r="3" class="pawan-dot"/>
<circle cx="665.8" cy="144.9" r="3" class="pawan-dot"/>
<circle cx="711.0" cy="128.4" r="3" class="pawan-dot"/>
<circle cx="726.0" cy="124.5" r="3" class="pawan-dot"/>
<text x="34.0" y="252" class="pawan-axis" text-anchor="middle">04 Aug</text>
<text x="726.0" y="252" class="pawan-axis" text-anchor="middle">19 Sep</text>
</svg>

The solid line is what the station at Model Town measured. The
dotted line is what Pawan said the day before, and the shaded
area is the range it gave. Observations arrive about three days
behind, so the most recent forecasts have nothing to sit against
yet.

## How it has done so far

Since the service started issuing forecasts it has made **9** of them, **7** of which have an observation to be checked against. On those, the mean absolute error is **4.6 &micro;g/m&sup3;** and the AQI band was right **7 times out of 7**.


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

<small>Generated from `data/predictions.json` at 2026-09-18T13:03:52+05:30.</small>
