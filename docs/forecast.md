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
<polygon points="403.1,95.5 449.2,97.8 464.6,93.7 480.0,111.8 495.3,101.3 510.7,121.5 526.1,103.2 572.2,104.1 587.6,99.5 603.0,106.2 618.4,99.2 649.1,77.4 664.5,89.0 679.9,90.6 695.2,83.5 710.6,106.0 726.0,126.0 726.0,179.2 710.6,169.4 695.2,158.3 679.9,160.8 664.5,160.0 649.1,154.2 618.4,160.6 603.0,164.3 587.6,160.7 572.2,163.3 526.1,203.1 510.7,221.5 495.3,201.2 480.0,211.4 464.6,193.3 449.2,197.4 403.1,198.2" class="pawan-band"/>
<polyline points="34.0,152.0 64.8,158.0 80.1,150.0 95.5,147.5 110.9,142.0 126.3,144.0 141.6,158.5 157.0,141.5 172.4,148.0 187.8,124.5 203.2,130.0 218.5,120.0 233.9,76.0 249.3,100.5 264.7,98.5 280.0,140.5 295.4,135.0 310.8,146.5 326.2,166.0 341.6,187.3 356.9,177.8 372.3,158.5 387.7,157.5 403.1,137.5 418.4,110.0 433.8,96.5 449.2,127.0 464.6,87.0 480.0,178.6 495.3,176.6 510.7,163.5 526.1,137.5 541.5,121.5 556.8,147.5 572.2,166.5 587.6,133.5 603.0,103.0 618.4,59.5 633.7,62.0 649.1,73.0 664.5,59.0" class="pawan-observed"/>
<polyline points="403.1,146.8 449.2,147.6 464.6,143.5 480.0,161.6 495.3,151.2 510.7,171.5 526.1,153.2 572.2,138.3 587.6,134.9 603.0,139.8 618.4,134.7 649.1,122.4 664.5,130.6 679.9,131.7 695.2,127.4 710.6,143.2 726.0,157.3" class="pawan-forecast"/>
<circle cx="403.1" cy="146.8" r="3" class="pawan-dot"/>
<circle cx="449.2" cy="147.6" r="3" class="pawan-dot"/>
<circle cx="464.6" cy="143.5" r="3" class="pawan-dot"/>
<circle cx="480.0" cy="161.6" r="3" class="pawan-dot"/>
<circle cx="495.3" cy="151.2" r="3" class="pawan-dot"/>
<circle cx="510.7" cy="171.5" r="3" class="pawan-dot"/>
<circle cx="526.1" cy="153.2" r="3" class="pawan-dot"/>
<circle cx="572.2" cy="138.3" r="3" class="pawan-dot"/>
<circle cx="587.6" cy="134.9" r="3" class="pawan-dot"/>
<circle cx="603.0" cy="139.8" r="3" class="pawan-dot"/>
<circle cx="618.4" cy="134.7" r="3" class="pawan-dot"/>
<circle cx="649.1" cy="122.4" r="3" class="pawan-dot"/>
<circle cx="664.5" cy="130.6" r="3" class="pawan-dot"/>
<circle cx="679.9" cy="131.7" r="3" class="pawan-dot"/>
<circle cx="695.2" cy="127.4" r="3" class="pawan-dot"/>
<circle cx="710.6" cy="143.2" r="3" class="pawan-dot"/>
<circle cx="726.0" cy="157.3" r="3" class="pawan-dot"/>
<text x="34.0" y="252" class="pawan-axis" text-anchor="middle">14 Aug</text>
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

<small>Generated from `data/predictions.json` at 2026-09-28T14:23:22+05:30.</small>
