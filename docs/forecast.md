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
<polygon points="380.0,95.5 427.2,97.8 442.9,93.7 458.6,111.8 474.4,101.3 490.1,121.5 505.8,103.2 553.0,104.1 568.7,99.5 584.5,106.2 600.2,99.2 631.6,77.4 647.4,89.0 663.1,90.6 678.8,83.5 694.5,106.0 710.3,126.0 710.3,179.2 694.5,169.4 678.8,158.3 663.1,160.8 647.4,160.0 631.6,154.2 600.2,160.6 584.5,164.3 568.7,160.7 553.0,163.3 505.8,203.1 490.1,221.5 474.4,201.2 458.6,211.4 442.9,193.3 427.2,197.4 380.0,198.2" class="pawan-band"/>
<polyline points="34.0,158.0 49.7,150.0 65.5,147.5 81.2,142.0 96.9,144.0 112.6,158.5 128.4,141.5 144.1,148.0 159.8,124.5 175.5,130.0 191.3,120.0 207.0,76.0 222.7,100.5 238.5,98.5 254.2,140.5 269.9,135.0 285.6,146.5 301.4,166.0 317.1,187.3 332.8,177.8 348.5,158.5 364.3,157.5 380.0,137.5 395.7,110.0 411.5,96.5 427.2,127.0 442.9,87.0 458.6,178.6 474.4,176.6 490.1,163.5 505.8,137.5 521.5,121.5 537.3,147.5 553.0,166.5 568.7,133.5 584.5,103.0 600.2,59.5 615.9,62.0 631.6,73.0 647.4,59.0 663.1,124.5 678.8,131.0 694.5,184.0 710.3,161.5 726.0,119.0" class="pawan-observed"/>
<polyline points="380.0,146.8 427.2,147.6 442.9,143.5 458.6,161.6 474.4,151.2 490.1,171.5 505.8,153.2 553.0,138.3 568.7,134.9 584.5,139.8 600.2,134.7 631.6,122.4 647.4,130.6 663.1,131.7 678.8,127.4 694.5,143.2 710.3,157.3" class="pawan-forecast"/>
<circle cx="380.0" cy="146.8" r="3" class="pawan-dot"/>
<circle cx="427.2" cy="147.6" r="3" class="pawan-dot"/>
<circle cx="442.9" cy="143.5" r="3" class="pawan-dot"/>
<circle cx="458.6" cy="161.6" r="3" class="pawan-dot"/>
<circle cx="474.4" cy="151.2" r="3" class="pawan-dot"/>
<circle cx="490.1" cy="171.5" r="3" class="pawan-dot"/>
<circle cx="505.8" cy="153.2" r="3" class="pawan-dot"/>
<circle cx="553.0" cy="138.3" r="3" class="pawan-dot"/>
<circle cx="568.7" cy="134.9" r="3" class="pawan-dot"/>
<circle cx="584.5" cy="139.8" r="3" class="pawan-dot"/>
<circle cx="600.2" cy="134.7" r="3" class="pawan-dot"/>
<circle cx="631.6" cy="122.4" r="3" class="pawan-dot"/>
<circle cx="647.4" cy="130.6" r="3" class="pawan-dot"/>
<circle cx="663.1" cy="131.7" r="3" class="pawan-dot"/>
<circle cx="678.8" cy="127.4" r="3" class="pawan-dot"/>
<circle cx="694.5" cy="143.2" r="3" class="pawan-dot"/>
<circle cx="710.3" cy="157.3" r="3" class="pawan-dot"/>
<text x="34.0" y="252" class="pawan-axis" text-anchor="middle">16 Aug</text>
<text x="726.0" y="252" class="pawan-axis" text-anchor="middle">29 Sep</text>
</svg>

The solid line is what the station at Model Town measured. The
dotted line is what Pawan said the day before, and the shaded
area is the range it gave. Observations arrive about three days
behind, so the most recent forecasts have nothing to sit against
yet.

## How it has done so far

Since the service started issuing forecasts it has made **17** of them, **17** of which have an observation to be checked against. On those, the mean absolute error is **5.6 &micro;g/m&sup3;** and the AQI band was right **14 times out of 17**.


That is the live record, not the backtest. It is short, and it
only covers a quiet time of year. [The full evaluation](results.md)
is the number to argue with.

| Day | Forecast | Observed | Error | Band |
| --- | ---: | ---: | ---: | :--- |
| 2026-09-28 | 13.8 | 12.9 | +0.8 | Good (correct) |
| 2026-09-27 | 16.6 | 8.4 | +8.2 | Good (correct) |
| 2026-09-26 | 19.7 | 19.0 | +0.7 | Good (correct) |
| 2026-09-25 | 18.9 | 20.3 | -1.4 | Good (correct) |
| 2026-09-24 | 19.1 | 33.4 | -14.3 | Good (missed) |
| 2026-09-23 | 20.7 | 30.6 | -9.9 | Good (missed) |
| 2026-09-21 | 18.3 | 33.3 | -15.0 | Good (missed) |
| 2026-09-20 | 17.2 | 24.6 | -7.4 | Good (correct) |
| 2026-09-19 | 18.2 | 18.5 | -0.3 | Good (correct) |
| 2026-09-18 | 17.5 | 11.9 | +5.6 | Good (correct) |


A forecast is written once and never revised. When the
observation for that day finally publishes it is filed beside the
original, untouched. Rewriting yesterday's forecast after
yesterday happened is the easiest way to build a system that
looks far better than it is.

<small>Generated from `data/predictions.json` at 2026-09-30T14:24:02+05:30.</small>
