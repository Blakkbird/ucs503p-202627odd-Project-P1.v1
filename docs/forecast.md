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
<polygon points="600.2,80.7 647.4,83.3 663.1,78.7 678.8,98.8 694.5,87.1 710.3,109.7 726.0,89.3 726.0,200.5 710.3,221.0 694.5,198.4 678.8,209.7 663.1,189.6 647.4,194.2 600.2,195.0" class="pawan-band"/>
<polyline points="34.0,161.4 49.7,148.1 65.5,185.0 81.2,155.9 96.9,126.9 112.6,167.6 128.4,112.5 144.1,159.8 159.8,139.7 175.5,145.3 191.3,147.5 207.0,130.8 222.7,143.6 254.2,150.3 269.9,141.4 285.6,138.6 301.4,132.5 317.1,134.7 332.8,150.9 348.5,131.9 364.3,139.2 380.0,113.0 395.7,119.1 411.5,108.0 427.2,59.0 442.9,86.3 458.6,84.1 474.4,130.8 490.1,124.7 505.8,137.5 521.5,159.2 537.3,182.9 553.0,172.3 568.7,150.9 584.5,149.8 600.2,127.5 615.9,96.9 631.6,81.9 647.4,115.8 663.1,71.3" class="pawan-observed"/>
<polyline points="600.2,137.8 647.4,138.7 663.1,134.2 678.8,154.3 694.5,142.7 710.3,165.3 726.0,144.9" class="pawan-forecast"/>
<circle cx="600.2" cy="137.8" r="3" class="pawan-dot"/>
<circle cx="647.4" cy="138.7" r="3" class="pawan-dot"/>
<circle cx="663.1" cy="134.2" r="3" class="pawan-dot"/>
<circle cx="678.8" cy="154.3" r="3" class="pawan-dot"/>
<circle cx="694.5" cy="142.7" r="3" class="pawan-dot"/>
<circle cx="710.3" cy="165.3" r="3" class="pawan-dot"/>
<circle cx="726.0" cy="144.9" r="3" class="pawan-dot"/>
<text x="34.0" y="252" class="pawan-axis" text-anchor="middle">02 Aug</text>
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

<small>Generated from `data/predictions.json` at 2026-09-16T13:21:02+05:30.</small>
