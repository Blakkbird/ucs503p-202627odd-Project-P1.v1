# Tomorrow in Patiala

<div class="pawan-card" style="border-left-color:#5ba829">
  <div class="pawan-when">Friday 02 October</div>
  <div class="pawan-value">23<span class="pawan-unit">&micro;g/m&sup3;</span></div>
  <div class="pawan-band-name" style="color:#5ba829">Good</div>
  <div class="pawan-note">likely range 16 to 33 &middot; issued 2026-10-01</div>
</div>


<svg viewBox="0 0 760 260" class="pawan-chart" role="img" aria-label="Observed and forecast PM2.5">
<line x1="34" y1="176.0" x2="726" y2="176.0" class="pawan-grid"/>
<text x="28" y="180.0" class="pawan-axis" text-anchor="end">10</text>
<line x1="34" y1="126.0" x2="726" y2="126.0" class="pawan-grid"/>
<text x="28" y="130.0" class="pawan-axis" text-anchor="end">20</text>
<line x1="34" y1="76.0" x2="726" y2="76.0" class="pawan-grid"/>
<text x="28" y="80.0" class="pawan-axis" text-anchor="end">30</text>
<polygon points="349.9,95.5 395.0,97.8 410.1,93.7 425.1,111.8 440.2,101.3 455.2,121.5 470.3,103.2 515.4,104.1 530.4,99.5 545.5,106.2 560.5,99.2 590.6,77.4 605.7,89.0 620.7,90.6 635.7,83.5 650.8,106.0 665.8,126.0 726.0,62.9 726.0,146.8 665.8,179.2 650.8,169.4 635.7,158.3 620.7,160.8 605.7,160.0 590.6,154.2 560.5,160.6 545.5,164.3 530.4,160.7 515.4,163.3 470.3,203.1 455.2,221.5 440.2,201.2 425.1,211.4 410.1,193.3 395.0,197.4 349.9,198.2" class="pawan-band"/>
<polyline points="34.0,150.0 49.0,147.5 64.1,142.0 79.1,144.0 94.2,158.5 109.2,141.5 124.3,148.0 139.3,124.5 154.3,130.0 169.4,120.0 184.4,76.0 199.5,100.5 214.5,98.5 229.6,140.5 244.6,135.0 259.7,146.5 274.7,166.0 289.7,187.3 304.8,177.8 319.8,158.5 334.9,157.5 349.9,137.5 365.0,110.0 380.0,96.5 395.0,127.0 410.1,87.0 425.1,178.6 440.2,176.6 455.2,163.5 470.3,137.5 485.3,121.5 500.3,147.5 515.4,166.5 530.4,133.5 545.5,103.0 560.5,59.5 575.6,62.0 590.6,73.0 605.7,59.0 620.7,124.5 635.7,131.0 650.8,184.0 665.8,161.5 680.9,119.0" class="pawan-observed"/>
<polyline points="349.9,146.8 395.0,147.6 410.1,143.5 425.1,161.6 440.2,151.2 455.2,171.5 470.3,153.2 515.4,138.3 530.4,134.9 545.5,139.8 560.5,134.7 590.6,122.4 605.7,130.6 620.7,131.7 635.7,127.4 650.8,143.2 665.8,157.3 726.0,112.1" class="pawan-forecast"/>
<circle cx="349.9" cy="146.8" r="3" class="pawan-dot"/>
<circle cx="395.0" cy="147.6" r="3" class="pawan-dot"/>
<circle cx="410.1" cy="143.5" r="3" class="pawan-dot"/>
<circle cx="425.1" cy="161.6" r="3" class="pawan-dot"/>
<circle cx="440.2" cy="151.2" r="3" class="pawan-dot"/>
<circle cx="455.2" cy="171.5" r="3" class="pawan-dot"/>
<circle cx="470.3" cy="153.2" r="3" class="pawan-dot"/>
<circle cx="515.4" cy="138.3" r="3" class="pawan-dot"/>
<circle cx="530.4" cy="134.9" r="3" class="pawan-dot"/>
<circle cx="545.5" cy="139.8" r="3" class="pawan-dot"/>
<circle cx="560.5" cy="134.7" r="3" class="pawan-dot"/>
<circle cx="590.6" cy="122.4" r="3" class="pawan-dot"/>
<circle cx="605.7" cy="130.6" r="3" class="pawan-dot"/>
<circle cx="620.7" cy="131.7" r="3" class="pawan-dot"/>
<circle cx="635.7" cy="127.4" r="3" class="pawan-dot"/>
<circle cx="650.8" cy="143.2" r="3" class="pawan-dot"/>
<circle cx="665.8" cy="157.3" r="3" class="pawan-dot"/>
<circle cx="726.0" cy="112.1" r="3" class="pawan-dot"/>
<text x="34.0" y="252" class="pawan-axis" text-anchor="middle">17 Aug</text>
<text x="726.0" y="252" class="pawan-axis" text-anchor="middle">02 Oct</text>
</svg>

The solid line is what the station at Model Town measured. The
dotted line is what Pawan said the day before, and the shaded
area is the range it gave. Observations arrive about three days
behind, so the most recent forecasts have nothing to sit against
yet.

## How it has done so far

Since the service started issuing forecasts it has made **18** of them, **17** of which have an observation to be checked against. On those, the mean absolute error is **5.6 &micro;g/m&sup3;** and the AQI band was right **14 times out of 17**.


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

<small>Generated from `data/predictions.json` at 2026-10-01T14:48:08+05:30.</small>
