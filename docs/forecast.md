# Tomorrow in Patiala

<div class="pawan-card" style="border-left-color:#5ba829">
  <div class="pawan-when">Thursday 24 September</div>
  <div class="pawan-value">19<span class="pawan-unit">&micro;g/m&sup3;</span></div>
  <div class="pawan-band-name" style="color:#5ba829">Good</div>
  <div class="pawan-note">likely range 13 to 27 &middot; issued 2026-09-23</div>
</div>


<svg viewBox="0 0 760 260" class="pawan-chart" role="img" aria-label="Observed and forecast PM2.5">
<line x1="34" y1="175.9" x2="726" y2="175.9" class="pawan-grid"/>
<text x="28" y="179.9" class="pawan-axis" text-anchor="end">10</text>
<line x1="34" y1="125.7" x2="726" y2="125.7" class="pawan-grid"/>
<text x="28" y="129.7" class="pawan-axis" text-anchor="end">20</text>
<line x1="34" y1="75.6" x2="726" y2="75.6" class="pawan-grid"/>
<text x="28" y="79.6" class="pawan-axis" text-anchor="end">30</text>
<polygon points="470.3,95.1 515.4,97.4 530.4,93.3 545.5,111.4 560.5,100.9 575.6,121.2 590.6,102.8 635.7,103.7 650.8,99.1 665.8,105.9 680.9,98.9 711.0,77.0 726.0,88.6 726.0,159.8 711.0,154.0 680.9,160.4 665.8,164.1 650.8,160.5 635.7,163.1 590.6,203.0 575.6,221.5 560.5,201.1 545.5,211.4 530.4,193.2 515.4,197.3 470.3,198.1" class="pawan-band"/>
<polyline points="34.0,166.3 49.0,148.3 64.1,153.3 79.1,155.3 94.2,140.3 109.2,151.8 139.3,157.8 154.3,149.8 169.4,147.3 184.4,141.8 199.5,143.8 214.5,158.3 229.6,141.3 244.6,147.8 259.7,124.2 274.7,129.7 289.7,119.7 304.8,75.6 319.8,100.2 334.9,98.2 349.9,140.3 365.0,134.8 380.0,146.3 395.0,165.8 410.1,187.2 425.1,177.6 440.2,158.3 455.2,157.3 470.3,137.3 485.3,109.7 500.3,96.1 515.4,126.7 530.4,86.6 545.5,178.5 560.5,176.5 575.6,163.3 590.6,137.3 605.7,121.2 620.7,147.3 635.7,166.3 650.8,133.2 665.8,102.7 680.9,59.0" class="pawan-observed"/>
<polyline points="470.3,146.6 515.4,147.4 530.4,143.3 545.5,161.4 560.5,151.0 575.6,171.4 590.6,153.0 635.7,138.1 650.8,134.6 665.8,139.6 680.9,134.4 711.0,122.1 726.0,130.3" class="pawan-forecast"/>
<circle cx="470.3" cy="146.6" r="3" class="pawan-dot"/>
<circle cx="515.4" cy="147.4" r="3" class="pawan-dot"/>
<circle cx="530.4" cy="143.3" r="3" class="pawan-dot"/>
<circle cx="545.5" cy="161.4" r="3" class="pawan-dot"/>
<circle cx="560.5" cy="151.0" r="3" class="pawan-dot"/>
<circle cx="575.6" cy="171.4" r="3" class="pawan-dot"/>
<circle cx="590.6" cy="153.0" r="3" class="pawan-dot"/>
<circle cx="635.7" cy="138.1" r="3" class="pawan-dot"/>
<circle cx="650.8" cy="134.6" r="3" class="pawan-dot"/>
<circle cx="665.8" cy="139.6" r="3" class="pawan-dot"/>
<circle cx="680.9" cy="134.4" r="3" class="pawan-dot"/>
<circle cx="711.0" cy="122.1" r="3" class="pawan-dot"/>
<circle cx="726.0" cy="130.3" r="3" class="pawan-dot"/>
<text x="34.0" y="252" class="pawan-axis" text-anchor="middle">09 Aug</text>
<text x="726.0" y="252" class="pawan-axis" text-anchor="middle">24 Sep</text>
</svg>

The solid line is what the station at Model Town measured. The
dotted line is what Pawan said the day before, and the shaded
area is the range it gave. Observations arrive about three days
behind, so the most recent forecasts have nothing to sit against
yet.

## How it has done so far

Since the service started issuing forecasts it has made **13** of them, **11** of which have an observation to be checked against. On those, the mean absolute error is **5.5 &micro;g/m&sup3;** and the AQI band was right **10 times out of 11**.


That is the live record, not the backtest. It is short, and it
only covers a quiet time of year. [The full evaluation](results.md)
is the number to argue with.

| Day | Forecast | Observed | Error | Band |
| --- | ---: | ---: | ---: | :--- |
| 2026-09-21 | 18.3 | 33.3 | -15.0 | Good (missed) |
| 2026-09-20 | 17.2 | 24.6 | -7.4 | Good (correct) |
| 2026-09-19 | 18.2 | 18.5 | -0.3 | Good (correct) |
| 2026-09-18 | 17.5 | 11.9 | +5.6 | Good (correct) |
| 2026-09-15 | 14.6 | 17.7 | -3.1 | Good (correct) |
| 2026-09-14 | 10.9 | 12.5 | -1.6 | Good (correct) |
| 2026-09-13 | 15.0 | 9.9 | +5.1 | Good (correct) |
| 2026-09-12 | 12.9 | 9.5 | +3.4 | Good (correct) |
| 2026-09-11 | 16.5 | 27.8 | -11.3 | Good (correct) |
| 2026-09-10 | 15.7 | 19.8 | -4.1 | Good (correct) |


A forecast is written once and never revised. When the
observation for that day finally publishes it is filed beside the
original, untouched. Rewriting yesterday's forecast after
yesterday happened is the easiest way to build a system that
looks far better than it is.

<small>Generated from `data/predictions.json` at 2026-09-23T13:24:47+05:30.</small>
