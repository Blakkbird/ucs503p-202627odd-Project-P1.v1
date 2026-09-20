# Tomorrow in Patiala

<div class="pawan-card" style="border-left-color:#5ba829">
  <div class="pawan-when">Monday 21 September</div>
  <div class="pawan-value">18<span class="pawan-unit">&micro;g/m&sup3;</span></div>
  <div class="pawan-band-name" style="color:#5ba829">Good</div>
  <div class="pawan-note">likely range 13 to 25 &middot; issued 2026-09-20</div>
</div>


<svg viewBox="0 0 760 260" class="pawan-chart" role="img" aria-label="Observed and forecast PM2.5">
<line x1="34" y1="170.3" x2="726" y2="170.3" class="pawan-grid"/>
<text x="28" y="174.3" class="pawan-axis" text-anchor="end">10</text>
<line x1="34" y1="114.7" x2="726" y2="114.7" class="pawan-grid"/>
<text x="28" y="118.7" class="pawan-axis" text-anchor="end">20</text>
<line x1="34" y1="59.0" x2="726" y2="59.0" class="pawan-grid"/>
<text x="28" y="63.0" class="pawan-axis" text-anchor="end">30</text>
<polygon points="515.4,80.7 560.5,83.3 575.6,78.7 590.6,98.8 605.7,87.1 620.7,109.7 635.7,89.3 680.9,90.3 695.9,85.1 711.0,92.7 726.0,84.9 726.0,153.2 711.0,157.3 695.9,153.3 680.9,156.2 635.7,200.5 620.7,221.0 605.7,198.4 590.6,209.7 575.6,189.6 560.5,194.2 515.4,195.0" class="pawan-band"/>
<polyline points="34.0,126.9 49.0,167.6 64.1,112.5 79.1,159.8 94.2,139.7 109.2,145.3 124.3,147.5 139.3,130.8 154.3,143.6 184.4,150.3 199.5,141.4 214.5,138.6 229.6,132.5 244.6,134.7 259.7,150.9 274.7,131.9 289.7,139.2 304.8,113.0 319.8,119.1 334.9,108.0 349.9,59.0 365.0,86.3 380.0,84.1 395.0,130.8 410.1,124.7 425.1,137.5 440.2,159.2 455.2,182.9 470.3,172.3 485.3,150.9 500.3,149.8 515.4,127.5 530.4,96.9 545.5,81.9 560.5,115.8 575.6,71.3 590.6,173.2 605.7,171.0 620.7,156.4 635.7,127.5 650.8,109.7 665.8,138.6" class="pawan-observed"/>
<polyline points="515.4,137.8 560.5,138.7 575.6,134.2 590.6,154.3 605.7,142.7 620.7,165.3 635.7,144.9 680.9,128.4 695.9,124.5 711.0,130.1 726.0,124.3" class="pawan-forecast"/>
<circle cx="515.4" cy="137.8" r="3" class="pawan-dot"/>
<circle cx="560.5" cy="138.7" r="3" class="pawan-dot"/>
<circle cx="575.6" cy="134.2" r="3" class="pawan-dot"/>
<circle cx="590.6" cy="154.3" r="3" class="pawan-dot"/>
<circle cx="605.7" cy="142.7" r="3" class="pawan-dot"/>
<circle cx="620.7" cy="165.3" r="3" class="pawan-dot"/>
<circle cx="635.7" cy="144.9" r="3" class="pawan-dot"/>
<circle cx="680.9" cy="128.4" r="3" class="pawan-dot"/>
<circle cx="695.9" cy="124.5" r="3" class="pawan-dot"/>
<circle cx="711.0" cy="130.1" r="3" class="pawan-dot"/>
<circle cx="726.0" cy="124.3" r="3" class="pawan-dot"/>
<text x="34.0" y="252" class="pawan-axis" text-anchor="middle">06 Aug</text>
<text x="726.0" y="252" class="pawan-axis" text-anchor="middle">21 Sep</text>
</svg>

The solid line is what the station at Model Town measured. The
dotted line is what Pawan said the day before, and the shaded
area is the range it gave. Observations arrive about three days
behind, so the most recent forecasts have nothing to sit against
yet.

## How it has done so far

Since the service started issuing forecasts it has made **11** of them, **7** of which have an observation to be checked against. On those, the mean absolute error is **4.6 &micro;g/m&sup3;** and the AQI band was right **7 times out of 7**.


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

<small>Generated from `data/predictions.json` at 2026-09-20T13:22:40+05:30.</small>
