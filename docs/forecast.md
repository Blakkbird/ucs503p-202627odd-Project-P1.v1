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
<polygon points="603.0,80.7 649.1,83.3 664.5,78.7 679.9,98.8 695.2,87.1 710.6,109.7 726.0,89.3 726.0,200.5 710.6,221.0 695.2,198.4 679.9,209.7 664.5,189.6 649.1,194.2 603.0,195.0" class="pawan-band"/>
<polyline points="34.0,162.6 49.4,161.4 64.8,148.1 80.1,185.0 95.5,155.9 110.9,126.9 126.3,167.6 141.6,112.5 157.0,159.8 172.4,139.7 187.8,145.3 203.2,147.5 218.5,130.8 233.9,143.6 264.7,150.3 280.0,141.4 295.4,138.6 310.8,132.5 326.2,134.7 341.6,150.9 356.9,131.9 372.3,139.2 387.7,113.0 403.1,119.1 418.4,108.0 433.8,59.0 449.2,86.3 464.6,84.1 480.0,130.8 495.3,124.7 510.7,137.5 526.1,159.2 541.5,182.9 556.8,172.3 572.2,150.9 587.6,149.8 603.0,127.5 618.4,96.9 633.7,81.9 649.1,115.8 664.5,71.3" class="pawan-observed"/>
<polyline points="603.0,137.8 649.1,138.7 664.5,134.2 679.9,154.3 695.2,142.7 710.6,165.3 726.0,144.9" class="pawan-forecast"/>
<circle cx="603.0" cy="137.8" r="3" class="pawan-dot"/>
<circle cx="649.1" cy="138.7" r="3" class="pawan-dot"/>
<circle cx="664.5" cy="134.2" r="3" class="pawan-dot"/>
<circle cx="679.9" cy="154.3" r="3" class="pawan-dot"/>
<circle cx="695.2" cy="142.7" r="3" class="pawan-dot"/>
<circle cx="710.6" cy="165.3" r="3" class="pawan-dot"/>
<circle cx="726.0" cy="144.9" r="3" class="pawan-dot"/>
<text x="34.0" y="252" class="pawan-axis" text-anchor="middle">01 Aug</text>
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

<small>Generated from `data/predictions.json` at 2026-09-15T13:28:04+05:30.</small>
