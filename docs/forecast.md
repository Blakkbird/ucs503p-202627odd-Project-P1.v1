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
<polygon points="510.7,80.7 556.8,83.3 572.2,78.7 587.6,98.8 603.0,87.1 618.4,109.7 633.7,89.3 679.9,90.3 695.2,85.1 710.6,92.7 726.0,84.9 726.0,153.2 710.6,157.3 695.2,153.3 679.9,156.2 633.7,200.5 618.4,221.0 603.0,198.4 587.6,209.7 572.2,189.6 556.8,194.2 510.7,195.0" class="pawan-band"/>
<polyline points="34.0,167.6 49.4,112.5 64.8,159.8 80.1,139.7 95.5,145.3 110.9,147.5 126.3,130.8 141.6,143.6 172.4,150.3 187.8,141.4 203.2,138.6 218.5,132.5 233.9,134.7 249.3,150.9 264.7,131.9 280.0,139.2 295.4,113.0 310.8,119.1 326.2,108.0 341.6,59.0 356.9,86.3 372.3,84.1 387.7,130.8 403.1,124.7 418.4,137.5 433.8,159.2 449.2,182.9 464.6,172.3 480.0,150.9 495.3,149.8 510.7,127.5 526.1,96.9 541.5,81.9 556.8,115.8 572.2,71.3 587.6,173.2 603.0,171.0 618.4,156.4 633.7,127.5 649.1,109.7 664.5,138.6" class="pawan-observed"/>
<polyline points="510.7,137.8 556.8,138.7 572.2,134.2 587.6,154.3 603.0,142.7 618.4,165.3 633.7,144.9 679.9,128.4 695.2,124.5 710.6,130.1 726.0,124.3" class="pawan-forecast"/>
<circle cx="510.7" cy="137.8" r="3" class="pawan-dot"/>
<circle cx="556.8" cy="138.7" r="3" class="pawan-dot"/>
<circle cx="572.2" cy="134.2" r="3" class="pawan-dot"/>
<circle cx="587.6" cy="154.3" r="3" class="pawan-dot"/>
<circle cx="603.0" cy="142.7" r="3" class="pawan-dot"/>
<circle cx="618.4" cy="165.3" r="3" class="pawan-dot"/>
<circle cx="633.7" cy="144.9" r="3" class="pawan-dot"/>
<circle cx="679.9" cy="128.4" r="3" class="pawan-dot"/>
<circle cx="695.2" cy="124.5" r="3" class="pawan-dot"/>
<circle cx="710.6" cy="130.1" r="3" class="pawan-dot"/>
<circle cx="726.0" cy="124.3" r="3" class="pawan-dot"/>
<text x="34.0" y="252" class="pawan-axis" text-anchor="middle">07 Aug</text>
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

<small>Generated from `data/predictions.json` at 2026-09-21T13:38:19+05:30.</small>
