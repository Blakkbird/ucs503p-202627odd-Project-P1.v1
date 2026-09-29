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
<polygon points="388.0,95.5 436.3,97.8 452.4,93.7 468.5,111.8 484.6,101.3 500.7,121.5 516.8,103.2 565.1,104.1 581.2,99.5 597.3,106.2 613.3,99.2 645.5,77.4 661.6,89.0 677.7,90.6 693.8,83.5 709.9,106.0 726.0,126.0 726.0,179.2 709.9,169.4 693.8,158.3 677.7,160.8 661.6,160.0 645.5,154.2 613.3,160.6 597.3,164.3 581.2,160.7 565.1,163.3 516.8,203.1 500.7,221.5 484.6,201.2 468.5,211.4 452.4,193.3 436.3,197.4 388.0,198.2" class="pawan-band"/>
<polyline points="34.0,158.0 50.1,150.0 66.2,147.5 82.3,142.0 98.4,144.0 114.5,158.5 130.6,141.5 146.7,148.0 162.7,124.5 178.8,130.0 194.9,120.0 211.0,76.0 227.1,100.5 243.2,98.5 259.3,140.5 275.4,135.0 291.5,146.5 307.6,166.0 323.7,187.3 339.8,177.8 355.9,158.5 372.0,157.5 388.0,137.5 404.1,110.0 420.2,96.5 436.3,127.0 452.4,87.0 468.5,178.6 484.6,176.6 500.7,163.5 516.8,137.5 532.9,121.5 549.0,147.5 565.1,166.5 581.2,133.5 597.3,103.0 613.3,59.5 629.4,62.0 645.5,73.0 661.6,59.0" class="pawan-observed"/>
<polyline points="388.0,146.8 436.3,147.6 452.4,143.5 468.5,161.6 484.6,151.2 500.7,171.5 516.8,153.2 565.1,138.3 581.2,134.9 597.3,139.8 613.3,134.7 645.5,122.4 661.6,130.6 677.7,131.7 693.8,127.4 709.9,143.2 726.0,157.3" class="pawan-forecast"/>
<circle cx="388.0" cy="146.8" r="3" class="pawan-dot"/>
<circle cx="436.3" cy="147.6" r="3" class="pawan-dot"/>
<circle cx="452.4" cy="143.5" r="3" class="pawan-dot"/>
<circle cx="468.5" cy="161.6" r="3" class="pawan-dot"/>
<circle cx="484.6" cy="151.2" r="3" class="pawan-dot"/>
<circle cx="500.7" cy="171.5" r="3" class="pawan-dot"/>
<circle cx="516.8" cy="153.2" r="3" class="pawan-dot"/>
<circle cx="565.1" cy="138.3" r="3" class="pawan-dot"/>
<circle cx="581.2" cy="134.9" r="3" class="pawan-dot"/>
<circle cx="597.3" cy="139.8" r="3" class="pawan-dot"/>
<circle cx="613.3" cy="134.7" r="3" class="pawan-dot"/>
<circle cx="645.5" cy="122.4" r="3" class="pawan-dot"/>
<circle cx="661.6" cy="130.6" r="3" class="pawan-dot"/>
<circle cx="677.7" cy="131.7" r="3" class="pawan-dot"/>
<circle cx="693.8" cy="127.4" r="3" class="pawan-dot"/>
<circle cx="709.9" cy="143.2" r="3" class="pawan-dot"/>
<circle cx="726.0" cy="157.3" r="3" class="pawan-dot"/>
<text x="34.0" y="252" class="pawan-axis" text-anchor="middle">16 Aug</text>
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

<small>Generated from `data/predictions.json` at 2026-09-29T14:25:12+05:30.</small>
