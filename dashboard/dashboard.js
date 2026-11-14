/* Pawan dashboard.
 *
 * Everything on the page comes from data.json, which code/pages.py
 * rewrites every morning. Nothing here computes a forecast of its
 * own except the what-if panel, and that one checks itself against
 * the pipeline before it is switched on (see checkParity).
 *
 * No framework and no build step. The page has to keep working
 * unattended for months, and the fewer moving parts it has the
 * fewer ways it has to break.
 */
(function () {
  "use strict";

  const $ = (id) => document.getElementById(id);
  const SVG = "http://www.w3.org/2000/svg";
  let D = null;  // data.json, once loaded

  // ---------------------------------------------------------------
  // small helpers

  function el(tag, attrs, text) {
    const node = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (k === "class") node.className = v;
      else if (k === "style") node.style.cssText = v;
      else node.setAttribute(k, v);
    }
    if (text != null) node.textContent = text;
    return node;
  }

  function svg(tag, attrs) {
    const node = document.createElementNS(SVG, tag);
    for (const [k, v] of Object.entries(attrs || {})) node.setAttribute(k, v);
    return node;
  }

  function cssVar(name) {
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  }

  const WEEKDAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
  const MONTHS = ["January", "February", "March", "April", "May", "June", "July",
                  "August", "September", "October", "November", "December"];

  function parseDay(iso) {
    const [y, m, d] = iso.slice(0, 10).split("-").map(Number);
    return new Date(Date.UTC(y, m - 1, d));
  }

  function dayName(iso, opts) {
    const t = parseDay(iso);
    const o = opts || {};
    let out = `${t.getUTCDate()} ${o.short ? MONTHS[t.getUTCMonth()].slice(0, 3) : MONTHS[t.getUTCMonth()]}`;
    if (o.weekday) out = `${o.short ? WEEKDAYS[t.getUTCDay()].slice(0, 3) : WEEKDAYS[t.getUTCDay()]} ${out}`;
    if (o.year) out += ` ${t.getUTCFullYear()}`;
    return out;
  }

  function stamp(isoTime) {
    // "2026-10-23T13:20:43+05:30" -> "23 October 2026, 13:20 IST"
    if (!isoTime) return "unknown";
    return `${dayName(isoTime, { year: true })}, ${isoTime.slice(11, 16)} IST`;
  }

  function daysBetween(a, b) {
    return Math.round((parseDay(b) - parseDay(a)) / 86400000);
  }

  function addDays(iso, n) {
    const t = parseDay(iso);
    t.setUTCDate(t.getUTCDate() + n);
    return t.toISOString().slice(0, 10);
  }

  const COMPASS = ["north", "north-east", "east", "south-east",
                   "south", "south-west", "west", "north-west"];
  function compass(deg) {
    return COMPASS[Math.round((((deg % 360) + 360) % 360) / 45) % 8];
  }

  function signed(frac) {
    const pct = Math.round(frac * 100);
    if (pct === 0) return "0%";
    return (pct > 0 ? "+" : "\u2212") + Math.abs(pct) + "%";
  }

  // ---------------------------------------------------------------
  // AQI bands

  function bandOf(value) {
    return D.bands.find((b) => b.upper === null || value <= b.upper);
  }

  function inkOn(hex) {
    // Dark text on light band colours, light text on dark ones.
    const n = parseInt(hex.slice(1), 16);
    const r = (n >> 16) & 255, g = (n >> 8) & 255, b = n & 255;
    return (0.299 * r + 0.587 * g + 0.114 * b) > 150 ? "#15212b" : "#ffffff";
  }

  function chip(band) {
    return el("span", { class: "chip", style: `background:${band.colour};color:${inkOn(band.colour)}` }, band.name);
  }

  // Position on the CPCB scale, 0..1. Six equal segments, the way
  // the scale is usually drawn, with a value placed proportionally
  // inside its own band. Severe has no top, so it is capped.
  function scalePos(value) {
    const i = D.bands.findIndex((b) => b.upper === null || value <= b.upper);
    const lower = i === 0 ? 0 : D.bands[i - 1].upper;
    const upper = D.bands[i].upper === null ? lower * 1.5 : D.bands[i].upper;
    const within = Math.min(Math.max((value - lower) / (upper - lower), 0), 1);
    return (i + within) / D.bands.length;
  }

  // ---------------------------------------------------------------
  // hero

  function renderHero() {
    const f = D.forecast;
    const hero = $("hero");
    const when = `Tomorrow, ${dayName(D.tomorrow, { weekday: true })}`;
    $("hero-when").textContent = when;

    const value = $("hero-value");
    value.textContent = "";
    if (!f) {
      value.textContent = "No forecast";
      value.style.fontSize = "clamp(2.6rem, 7vw, 4.5rem)";
      $("hero-range").textContent = `The daily job could not issue one: ${D.missing_reason}.`;
      $("hero-advice").textContent = "This usually clears on the next morning's run.";
      hero.style.setProperty("--haze-mix", "6%");
    } else {
      const band = bandOf(f.pm25);
      value.append(String(Math.round(f.pm25)), el("span", { class: "unit" }, "\u00b5g/m\u00b3"));
      $("hero-band").replaceChildren(chip(band));
      if (f.interval) {
        $("hero-range").textContent =
          `Likely between ${Math.round(f.interval[0])} and ${Math.round(f.interval[1])}`;
      }
      $("hero-advice").textContent = band.advice;
      // The haze thickens with the number, up to a point.
      const mix = Math.min(6 + (f.pm25 / 250) * 42, 48);
      hero.style.setProperty("--haze-mix", `${mix.toFixed(1)}%`);
    }

    renderScale();

    const raw = (D.inputs || {}).raw || {};
    const parts = [];
    if (raw.cams != null) {
      parts.push(`CAMS, the global forecast Pawan corrects, says ${Math.round(raw.cams)} for the same day.`);
    }
    if (raw.obs_recent != null && raw.obs_day) {
      parts.push(`The newest full day the station has published is ${dayName(raw.obs_day)}, at ${raw.obs_recent.toFixed(1)}.`);
    }
    $("hero-compare").textContent = parts.join(" ");

    hero.classList.add("ready");
    document.title = f
      ? `${Math.round(f.pm25)} \u00b5g/m\u00b3 tomorrow in Patiala | Pawan`
      : "Pawan: tomorrow's air in Patiala";
  }

  function renderScale() {
    const box = $("scale");
    box.replaceChildren();
    const bar = el("div", { class: "scale-bar" });
    const labels = el("div", { class: "scale-labels" });
    D.bands.forEach((b, i) => {
      bar.append(el("span", { class: "scale-seg", style: `background:${b.colour}` }));
      const lower = i === 0 ? 0 : D.bands[i - 1].upper + 1;
      labels.append(el("span", {}, `${b.name}`));
      labels.lastChild.append(el("br"), `${lower}${b.upper === null ? "+" : "\u2013" + b.upper}`);
    });
    box.append(bar, labels);

    const f = D.forecast;
    const raw = (D.inputs || {}).raw || {};
    if (f && f.interval) {
      const a = scalePos(f.interval[0]), b = scalePos(f.interval[1]);
      box.append(el("div", { class: "scale-range", style: `left:${a * 100}%;width:${(b - a) * 100}%` }));
    }

    // Pins sit above the bar. Ones that would overlap are lifted
    // a level, so a close CAMS and Pawan stay readable.
    const pins = [];
    if (f) pins.push({ cls: "pin-pawan", label: "Pawan", value: f.pm25 });
    if (raw.cams != null) pins.push({ cls: "pin-cams", label: "CAMS", value: raw.cams });
    if (raw.obs_recent != null) pins.push({ cls: "pin-obs", label: "Last reading", value: raw.obs_recent });
    pins.forEach((p) => { p.pos = scalePos(p.value); });
    const placed = [];
    for (const p of pins.slice().sort((a, b) => a.pos - b.pos)) {
      p.level = 0;
      while (placed.some((q) => q.level === p.level && Math.abs(q.pos - p.pos) < 0.15)) p.level++;
      placed.push(p);
    }
    const levels = Math.max(1, ...pins.map((p) => p.level + 1));
    const ROW = 2.5;  // rem per level
    box.style.paddingTop = `${levels * ROW + 0.4}rem`;
    box.style.setProperty("--bar-top", `${levels * ROW + 0.4}rem`);
    for (const p of pins) {
      const pin = el("div", { class: `scale-pin ${p.cls}`,
        style: `left:${p.pos * 100}%;top:${(levels - 1 - p.level) * ROW}rem;--stem:${(p.level + 1) * ROW - 0.85}rem` });
      const label = el("div", { class: "pin-label" });
      label.append(el("b", {}, String(Math.round(p.value))), " ", p.label);
      pin.append(label);
      box.append(pin);
    }
  }

  // ---------------------------------------------------------------
  // notices: things a reader should know before trusting the page

  function renderNotices() {
    const notes = [];
    const h = D.health || {};
    if (h.obs_age_days != null && h.obs_age_days > h.stale_after_days) {
      notes.push(`The station has not published a reading for ${h.obs_age_days} days. Forecasts carry on from older readings, and the daily job is flagging it.`);
    }
    const age = (Date.now() - Date.parse(D.generated_at)) / 3600000;
    if (age > 36) {
      notes.push(`This page was last rebuilt ${stamp(D.generated_at)}. The morning job may not have run since.`);
    }
    if (notes.length) {
      const box = $("notice");
      box.textContent = notes.join(" ");
      box.hidden = false;
    }
  }

  // ---------------------------------------------------------------
  // fire map

  // A point `km` away from (lat, lon) along a compass bearing.
  function destination(lat, lon, bearing, km) {
    const R = 6371, d = km / R, b = bearing * Math.PI / 180;
    const p1 = lat * Math.PI / 180, l1 = lon * Math.PI / 180;
    const p2 = Math.asin(Math.sin(p1) * Math.cos(d) + Math.cos(p1) * Math.sin(d) * Math.cos(b));
    const l2 = l1 + Math.atan2(Math.sin(b) * Math.sin(d) * Math.cos(p1),
                               Math.cos(d) - Math.sin(p1) * Math.sin(p2));
    return [p2 * 180 / Math.PI, l2 * 180 / Math.PI];
  }

  function renderFires() {
    const F = D.fires;
    const frame = document.querySelector(".map-frame");
    if (!F) {
      $("fires-lede").textContent = "Fire positions have not been recorded yet. The daily job keeps them from its next run onwards.";
      frame.replaceChildren(el("p", { class: "map-fallback" }, "No fire positions on record yet."));
      $("fires-key").replaceChildren();
      return;
    }

    const newest = F.days[0];
    const older = F.days[1];
    const speed = F.wind_speed, from = F.wind_from;
    let wind = "";
    if (from == null) {
      wind = "Tomorrow's wind forecast is missing, so no upwind wedge is drawn.";
    } else if (speed < 3) {
      wind = `Tomorrow's wind is forecast to be light (${speed.toFixed(1)} km/h), so smoke would drift slowly whichever way it came from.`;
    } else {
      wind = `Tomorrow's wind is forecast to come from the ${compass(from)} at ${speed.toFixed(0)} km/h, which puts ${newest.upwind} of them upwind of Patiala.`;
    }
    $("fires-lede").textContent =
      `${newest.fires} fires were detected by satellite across Punjab and Haryana on ${dayName(newest.day)}. ${wind}`;

    const key = $("fires-key");
    key.replaceChildren();
    const row = (dot, text, count) => {
      const li = el("li");
      li.append(dot, el("span", {}, text));
      if (count != null) li.append(el("span", { class: "key-count" }, String(count)));
      key.append(li);
    };
    if (from != null) row(el("span", { class: "key-dot up" }), `Upwind, ${dayName(newest.day)}`, newest.upwind);
    row(el("span", { class: "key-dot other" }), from != null ? "Elsewhere in the area" : dayName(newest.day),
        newest.fires - (from != null ? newest.upwind : 0));
    if (older) row(el("span", { class: "key-dot old" }), `The day before, ${dayName(older.day)}`, older.fires);
    if (from != null) row(el("span", { class: "key-wedge" }), `Upwind wedge, ${F.half_angle}\u00b0 either side of the wind, out to ${F.range_km} km`);
    row(el("span", { class: "key-station" }), "Model Town station, Patiala");

    $("fires-note").textContent =
      "The model reads the total count for the whole area. The wedge only shows where tomorrow's air is coming from. Larger dots are fires burning with more power.";

    if (!window.L) {
      frame.replaceChildren(el("p", { class: "map-fallback" },
        "The map library did not load, so the map is not shown. The counts on the right are unaffected."));
      return;
    }

    const dark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
    const map = L.map("map", { preferCanvas: true, scrollWheelZoom: false, minZoom: 5, maxZoom: 12 });
    L.tileLayer(`https://{s}.basemaps.cartocdn.com/${dark ? "dark_all" : "light_all"}/{z}/{x}/{y}{r}.png`, {
      subdomains: "abcd",
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
    }).addTo(map);

    // Frame what is worth looking at: the station, yesterday's
    // fires and the wedge. The fetch box is much larger than the
    // area that actually burns, and fitting to it leaves the fires
    // in a corner.
    const frameOn = [[D.station.lat, D.station.lon]];
    F.points.forEach((p) => { if (p[4] === 0) frameOn.push([p[0], p[1]]); });
    if (frameOn.length < 3) {
      const [w, s, e, n] = F.bbox;
      frameOn.push([s, w], [n, e]);
    }
    map.fitBounds(L.latLngBounds(frameOn).pad(0.12), { maxZoom: 9 });

    const ember = cssVar("--ember"), pawan = cssVar("--pawan"), ink = cssVar("--ink"), sky = cssVar("--sky");
    const lat = D.station.lat, lon = D.station.lon;

    if (from != null) {
      const arc = [[lat, lon]];
      for (let b = from - F.half_angle; b <= from + F.half_angle; b += 3) {
        arc.push(destination(lat, lon, b, F.range_km));
      }
      L.polygon(arc, { color: pawan, weight: 1, fillColor: pawan, fillOpacity: 0.08, interactive: false }).addTo(map);

      // The wind itself, blowing in towards the station.
      if (speed >= 3) {
        const tail = destination(lat, lon, from, F.range_km * 0.62);
        const head = destination(lat, lon, from, 22);
        L.polyline([tail, head], { color: pawan, weight: 3, interactive: false }).addTo(map);
        const back = (from + 180) % 360;  // direction the wind travels
        for (const side of [-150, 150]) {
          L.polyline([head, destination(head[0], head[1], back + side, 26)],
            { color: pawan, weight: 3, interactive: false }).addTo(map);
        }
      }
    }

    // Oldest first, so yesterday's fires draw on top.
    const pts = F.points.slice().sort((a, b) => b[4] - a[4] || a[3] - b[3]);
    for (const [plat, plon, frp, up, age, low] of pts) {
      const r = 2.2 + Math.min(Math.sqrt(frp), 6) * 0.65;
      if (age > 0) {
        L.circleMarker([plat, plon], { radius: r * 0.8, color: ember, weight: 1, opacity: 0.45, fill: false }).addTo(map);
      } else {
        L.circleMarker([plat, plon], {
          radius: r, stroke: false, fillColor: ember,
          fillOpacity: (up ? 0.9 : 0.32) * (low ? 0.6 : 1),
        }).addTo(map);
      }
    }

    L.circleMarker([lat, lon], { radius: 7, color: ink, weight: 3, fillColor: sky, fillOpacity: 1 })
      .bindTooltip("Patiala", { permanent: true, direction: "right", offset: [10, 0], className: "station-label" })
      .addTo(map);
  }

  // ---------------------------------------------------------------
  // what goes into the number, and the what-if sliders

  // How each reading becomes model inputs. This repeats
  // features.transform() in code/features.py line for line; if the
  // two ever disagree, checkParity turns the sliders off.
  function transform(raw, burning, names) {
    const log1p = (v) => (v == null ? null : Math.log1p(v));
    const has = (v) => v !== null && v !== undefined;
    let u = null, v = null;
    if (has(raw.wind_speed) && has(raw.wind_dir)) {
      const rad = raw.wind_dir * (Math.PI / 180);  // as math.radians does it
      u = -raw.wind_speed * Math.sin(rad);
      v = -raw.wind_speed * Math.cos(rad);
    }
    const vals = {
      cams_log: log1p(raw.cams),
      obs_recent_log: log1p(raw.obs_recent),
      burning: burning ? 1.0 : 0.0,
      temp: has(raw.temp) ? raw.temp : null,
      rh: has(raw.rh) ? raw.rh : null,
      wind_speed: has(raw.wind_speed) ? raw.wind_speed : null,
      wind_u: u,
      wind_v: v,
      fire_log: log1p(raw.fires),
    };
    for (const [name, pair] of Object.entries(D.model.interactions || {})) {
      const a = vals[pair[0]], b = vals[pair[1]];
      vals[name] = a == null || b == null ? null : a * b;
    }
    return names.map((n) => (n in vals ? vals[n] : undefined));
  }

  function linear(x) {
    const m = D.model;
    let total = m.intercept;
    const terms = [];
    for (let j = 0; j < m.names.length; j++) {
      const t = m.coef[j] * (x[j] - m.means[j]) / m.devs[j];
      terms.push(t);
      total += t;
    }
    let point = m.log_target ? Math.expm1(total) : total;
    return { point: Math.max(point, 0), terms };
  }

  function groupTerms(terms) {
    // Grouped by pages.GROUPS, which comes in the data file, so the
    // page and the pipeline cannot group the inputs differently.
    const groups = D.model.groups || {};
    const byKey = {};
    D.model.names.forEach((name, j) => {
      const key = groups[name] || name;
      byKey[key] = (byKey[key] || 0) + terms[j];
    });
    return byKey;
  }

  // The vector rebuilt here has to match the one the pipeline
  // used, input for input, and give the same forecast. If not, the
  // breakdown still shows (it comes from Python), but the sliders
  // stay off rather than show numbers the model would not give.
  function checkParity() {
    const I = D.inputs, M = D.model;
    if (!I || !M || !I.complete || M.now == null) return "tomorrow's inputs are incomplete";
    const x = transform(I.raw, I.burning, I.names);
    for (let j = 0; j < x.length; j++) {
      if (x[j] == null || Math.abs(x[j] - I.x[j]) > 1e-9 * Math.max(1, Math.abs(I.x[j]))) {
        return `the page and the pipeline disagree on ${I.names[j]}`;
      }
    }
    const got = linear(x).point;
    if (Math.abs(got - M.now) > 1e-6 * Math.max(1, M.now)) {
      return "the page and the pipeline disagree on the forecast";
    }
    return null;
  }

  // Slider definitions, keyed by group. `log` sliders move evenly
  // in log space, which is how the model sees those inputs.
  const SLIDERS = {
    cams: { raw: "cams", min: 5, max: 400, log: true, show: (v) => `${Math.round(v)} \u00b5g/m\u00b3` },
    station: { raw: "obs_recent", min: 3, max: 300, log: true, show: (v) => `${v.toFixed(1)} \u00b5g/m\u00b3` },
    fires: { raw: "fires", min: 0, max: 3000, log: true, show: (v) => `${Math.round(v)} fires` },
    rh: { raw: "rh", min: 10, max: 100, show: (v) => `${Math.round(v)}%` },
    temp: { raw: "temp", min: 0, max: 45, show: (v) => `${v.toFixed(1)} \u00b0C` },
    wind_speed: { raw: "wind_speed", min: 0, max: 30, show: (v) => `${v.toFixed(1)} km/h` },
    wind_dir: { raw: "wind_dir", min: 0, max: 359, show: (v) => `from the ${compass(v)} (${Math.round(v)}\u00b0)` },
  };

  const STEPS = 1000;
  function toPos(s, v) {
    if (s.log) return Math.round((Math.log1p(v) - Math.log1p(s.min)) / (Math.log1p(s.max) - Math.log1p(s.min)) * STEPS);
    return Math.round((v - s.min) / (s.max - s.min) * STEPS);
  }
  function fromPos(s, p) {
    const f = p / STEPS;
    if (s.log) return Math.expm1(Math.log1p(s.min) + f * (Math.log1p(s.max) - Math.log1p(s.min)));
    return s.min + f * (s.max - s.min);
  }

  const EFFECT_SPAN = 0.45;  // log units at either end of the bar

  function renderDrivers() {
    const box = $("drivers");
    box.replaceChildren();
    if (!D.why || !D.model) {
      $("why-lede").textContent = "Tomorrow's inputs are incomplete, so there is no forecast to break down.";
      return;
    }

    const typical = D.model.typical;
    $("why-lede").textContent =
      `The model starts from a typical day in this station's record, about ${Math.round(typical)} \u00b5g/m\u00b3. ` +
      "Each input then pushes tomorrow's number up or down by the share shown, and the pushes multiply together. " +
      "Because the model is linear in these inputs, the breakdown is exact.";

    const problem = checkParity();
    const live = !problem;
    const base = D.inputs.raw;
    const state = Object.assign({}, base);
    const rows = {};

    for (const g of D.why) {
      const row = el("div", { class: "driver" });
      const name = el("div");
      name.append(el("span", { class: "driver-name" }, g.label));
      const valueText = el("span", { class: "driver-value" });
      name.append(valueText);
      row.append(name);

      const s = SLIDERS[g.key];
      let input = null;
      if (s && live && base[s.raw] != null) {
        input = el("input", {
          type: "range", min: "0", max: String(STEPS), step: "1",
          value: String(toPos(s, Math.min(Math.max(base[s.raw], s.min), s.max))),
          "aria-label": g.label,
        });
        input.addEventListener("input", () => {
          state[s.raw] = fromPos(s, Number(input.value));
          update();
        });
        row.append(input);
      } else {
        const why = g.key === "season" ? "Set by the date, so it has no slider."
          : live ? "" : "Slider off.";
        row.append(el("span", { class: "driver-fixed" }, why));
      }

      const effect = el("div", { class: "effect" });
      const track = el("div", { class: "effect-track" });
      const bar = el("div", { class: "effect-bar" });
      track.append(bar);
      const text = el("span", { class: "effect-text" });
      effect.append(track, text);
      row.append(effect);

      box.append(row);
      rows[g.key] = { s, valueText, bar, text, input };
    }

    function describe(key, raw) {
      const s = SLIDERS[key];
      if (key === "season") return D.inputs.burning ? "On, October and November" : "Off";
      if (key === "fires" && raw.fire_day) return `${s.show(raw.fires)} on ${dayName(raw.fire_day)}`;
      if (key === "station" && raw.obs_day) return `${s.show(raw.obs_recent)} on ${dayName(raw.obs_day)}`;
      if (s && raw[s.raw] != null) return s.show(raw[s.raw]);
      return "";
    }

    function draw(termsByKey, raw) {
      for (const [key, r] of Object.entries(rows)) {
        const t = termsByKey[key] || 0;
        const w = Math.min(Math.abs(t) / EFFECT_SPAN, 1) * 50;
        r.bar.className = `effect-bar ${t >= 0 ? "up" : "down"}`;
        r.bar.style.left = t >= 0 ? "50%" : `${50 - w}%`;
        r.bar.style.width = `${w}%`;
        r.text.textContent = D.model.log_target ? signed(Math.expm1(t)) : `${t >= 0 ? "+" : "\u2212"}${Math.abs(t).toFixed(1)}`;
        r.valueText.textContent = describe(key, raw);
      }
    }

    function result(point, changed) {
      const band = bandOf(point);
      const out = $("why-result");
      out.replaceChildren();
      const rest = D.forecast ? "Tomorrow's forecast" : "What the model gives for these inputs";
      out.append(el("span", { class: "sub" }, changed ? "With your changes" : rest));
      out.append(el("span", { class: "num" }, String(Math.round(point))));
      const sub = el("span", { class: "sub" });
      sub.append("\u00b5g/m\u00b3, ", chip(band));
      out.append(sub);
      if (changed) {
        const diff = point - D.model.now;
        out.append(el("span", { class: "sub", style: "display:block" },
          `${diff >= 0 ? "+" : "\u2212"}${Math.abs(diff).toFixed(0)} on the real forecast`));
      }
    }

    function update() {
      const x = transform(state, D.inputs.burning, D.inputs.names);
      const got = linear(x);
      const changed = Object.keys(SLIDERS).some((k) => {
        const key = SLIDERS[k].raw;
        return state[key] != null && Math.abs(state[key] - base[key]) > 1e-9;
      });
      draw(groupTerms(got.terms), state);
      result(got.point, changed);
      $("why-reset").hidden = !changed;
    }

    // First draw straight from the pipeline's own breakdown.
    const initial = {};
    D.why.forEach((g) => { initial[g.key] = g.term; });
    draw(initial, base);
    result(D.model.now, false);

    $("why-reset").onclick = () => {
      Object.assign(state, base);
      for (const r of Object.values(rows)) {
        if (r.input) r.input.value = String(toPos(r.s, Math.min(Math.max(base[r.s.raw], r.s.min), r.s.max)));
      }
      update();
      draw(initial, base);
    };

    $("why-note").textContent = live
      ? "Move a slider to see what the model would say if that reading were different. These are the weights the model learnt from this station's history: what has tended to come with cleaner or dirtier days here, not a chemistry model."
      : `The sliders are switched off because ${problem}. The breakdown above comes straight from the pipeline and is unaffected.`;
  }

  // ---------------------------------------------------------------
  // history chart

  const RANGES = [];
  const SHOW = { observed: true, cams: true, pawan: true, range: true };
  let RANGE = "90";

  function buildRanges() {
    const end = D.tomorrow;
    const t = parseDay(end);
    const lastSeason = t.getUTCMonth() >= 11 ? t.getUTCFullYear() : t.getUTCFullYear() - 1;
    RANGES.length = 0;
    RANGES.push({ key: "30", label: "30 days", from: addDays(end, -29), to: end });
    RANGES.push({ key: "90", label: "90 days", from: addDays(end, -89), to: end });
    RANGES.push({ key: "season", label: `Burning season ${lastSeason}`, from: `${lastSeason}-10-01`, to: `${lastSeason}-11-30` });
    RANGES.push({ key: "all", label: "Everything", from: D.history.dates[0], to: end });

    const box = $("range-buttons");
    box.replaceChildren();
    for (const r of RANGES) {
      const b = el("button", { type: "button", "aria-pressed": String(r.key === RANGE) }, r.label);
      b.onclick = () => {
        RANGE = r.key;
        box.querySelectorAll("button").forEach((x) => x.setAttribute("aria-pressed", "false"));
        b.setAttribute("aria-pressed", "true");
        drawChart();
      };
      box.append(b);
    }

    const sbox = $("series-buttons");
    sbox.replaceChildren();
    const series = [
      ["observed", "Measured", "", "color:var(--observed)"],
      ["cams", "CAMS", "dashed", "color:var(--cams)"],
      ["pawan", "Pawan", "", "color:var(--pawan)"],
      ["range", "Likely range", "band", ""],
    ];
    for (const [key, label, kind, style] of series) {
      const b = el("button", { type: "button", "aria-pressed": "true", style });
      b.append(el("span", { class: `swatch ${kind}` }), label);
      b.onclick = () => {
        SHOW[key] = !SHOW[key];
        b.setAttribute("aria-pressed", String(SHOW[key]));
        drawChart();
      };
      sbox.append(b);
    }
  }

  function niceStep(top) {
    for (const s of [10, 20, 25, 50, 100]) if (top / s <= 6) return s;
    return 200;
  }

  function drawChart() {
    const H = D.history;
    const box = $("chart");
    box.replaceChildren();
    const range = RANGES.find((r) => r.key === RANGE);
    const i0 = Math.max(0, H.dates.indexOf(range.from) >= 0 ? H.dates.indexOf(range.from) : daysBetween(H.dates[0], range.from));
    let i1 = H.dates.indexOf(range.to);
    if (i1 < 0) i1 = H.dates.length - 1;
    const idx = [];
    for (let i = Math.max(i0, 0); i <= i1; i++) idx.push(i);
    if (idx.length < 2) {
      box.append(el("p", { class: "map-fallback" }, "Nothing on record for this range."));
      return;
    }

    const W = box.clientWidth || 800, Ht = box.clientHeight || 320;
    const m = { l: 42, r: 14, t: 12, b: 26 };
    const pick = (arr) => idx.map((i) => arr[i]).filter((v) => v != null);
    let top = 0;
    const consider = [];
    if (SHOW.observed) consider.push(...pick(H.observed));
    if (SHOW.cams) consider.push(...pick(H.cams));
    if (SHOW.pawan) consider.push(...pick(H.backtest), ...pick(H.forecast));
    if (SHOW.range) consider.push(...pick(H.high));
    top = Math.max(40, ...consider) * 1.08;

    const x = (i) => m.l + (i - idx[0]) / (idx[idx.length - 1] - idx[0]) * (W - m.l - m.r);
    const y = (v) => Ht - m.b - (v / top) * (Ht - m.t - m.b);

    const root = svg("svg", { viewBox: `0 0 ${W} ${Ht}`, role: "img",
      "aria-label": `PM2.5 at Model Town from ${dayName(H.dates[idx[0]], { year: true })} to ${dayName(H.dates[idx[idx.length - 1]], { year: true })}` });

    // AQI bands as a strip along the axis, so a reader can see
    // which band a line is in without reading numbers.
    let lower = 0;
    for (const b of D.bands) {
      if (lower >= top) break;
      const upper = b.upper === null ? top : Math.min(b.upper, top);
      root.append(svg("rect", { x: m.l - 4, y: y(upper), width: 4, height: y(lower) - y(upper), fill: b.colour }));
      lower = b.upper === null ? top : b.upper;
    }

    const step = niceStep(top);
    for (let v = step; v < top; v += step) {
      root.append(svg("line", { x1: m.l, x2: W - m.r, y1: y(v), y2: y(v), class: "grid" }));
      const t = svg("text", { x: m.l - 9, y: y(v) + 4, "text-anchor": "end", class: "axis" });
      t.textContent = v;
      root.append(t);
    }

    // Date ticks: weekly on short ranges, monthly on medium ones,
    // quarterly when the whole record is on screen.
    const span = idx.length;
    for (const i of idx) {
      const day = parseDay(H.dates[i]);
      const month = day.getUTCMonth();
      let label = null;
      if (span <= 45) {
        if (day.getUTCDay() === 1) label = dayName(H.dates[i], { short: true });
      } else if (day.getUTCDate() === 1) {
        if (span <= 400) label = MONTHS[month].slice(0, 3) + (month === 0 ? ` ${day.getUTCFullYear()}` : "");
        else if (month % 3 === 0) label = `${MONTHS[month].slice(0, 3)} ${day.getUTCFullYear()}`;
      }
      if (!label) continue;
      const t = svg("text", { x: x(i), y: Ht - 8, "text-anchor": "middle", class: "axis" });
      t.textContent = label;
      root.append(t);
    }

    // Today, so it is clear why the measured line stops short.
    const ti = H.dates.indexOf(D.today);
    if (ti >= idx[0] && ti <= idx[idx.length - 1]) {
      root.append(svg("line", { x1: x(ti), x2: x(ti), y1: m.t, y2: Ht - m.b, stroke: cssVar("--muted"),
        "stroke-dasharray": "2 4", "stroke-width": 1 }));
      const t = svg("text", { x: x(ti) - 4, y: m.t + 10, "text-anchor": "end", class: "axis" });
      t.textContent = "today";
      root.append(t);
    }

    const path = (arr) => {
      let d = "", pen = false;
      for (const i of idx) {
        const v = arr[i];
        if (v == null) { pen = false; continue; }
        d += `${pen ? "L" : "M"}${x(i).toFixed(1)},${y(v).toFixed(1)}`;
        pen = true;
      }
      return d;
    };

    if (SHOW.range) {
      // One polygon per unbroken run of ranged days.
      let run = [];
      const flush = () => {
        if (run.length > 1) {
          const upper = run.map((i) => `${x(i).toFixed(1)},${y(H.high[i]).toFixed(1)}`);
          const lowerPts = run.slice().reverse().map((i) => `${x(i).toFixed(1)},${y(H.low[i]).toFixed(1)}`);
          root.append(svg("polygon", { points: upper.concat(lowerPts).join(" "), fill: cssVar("--pawan-soft") }));
        }
        run = [];
      };
      for (const i of idx) {
        if (H.low[i] != null && H.high[i] != null) run.push(i); else flush();
      }
      flush();
    }

    if (SHOW.cams) {
      root.append(svg("path", { d: path(H.cams), fill: "none", stroke: cssVar("--cams"), "stroke-width": 1.6,
        "stroke-dasharray": "5 4", "stroke-linejoin": "round" }));
    }
    if (SHOW.pawan) {
      root.append(svg("path", { d: path(H.backtest), fill: "none", stroke: cssVar("--pawan"), "stroke-width": 1.5,
        opacity: 0.6, "stroke-linejoin": "round" }));
      root.append(svg("path", { d: path(H.forecast), fill: "none", stroke: cssVar("--pawan"), "stroke-width": 2.4,
        "stroke-linejoin": "round" }));
      if (span <= 120) {
        for (const i of idx) {
          if (H.forecast[i] != null) root.append(svg("circle", { cx: x(i), cy: y(H.forecast[i]), r: 2.6, fill: cssVar("--pawan") }));
        }
      }
    }
    if (SHOW.observed) {
      root.append(svg("path", { d: path(H.observed), fill: "none", stroke: cssVar("--observed"), "stroke-width": 2,
        "stroke-linejoin": "round" }));
      if (span <= 120) {
        for (const i of idx) {
          if (H.thin[i] && H.observed[i] != null) {
            root.append(svg("circle", { cx: x(i), cy: y(H.observed[i]), r: 3, fill: cssVar("--surface"),
              stroke: cssVar("--observed"), "stroke-width": 1.4 }));
          }
        }
      }
    }

    // Hover and keyboard read-out.
    const cross = svg("line", { y1: m.t, y2: Ht - m.b, stroke: cssVar("--ink"), "stroke-width": 1, opacity: 0 });
    root.append(cross);
    const hit = svg("rect", { x: m.l, y: m.t, width: W - m.l - m.r, height: Ht - m.t - m.b, fill: "transparent" });
    root.append(hit);
    box.append(root);

    const tip = $("tip");
    let at = null;
    const frame = box.parentElement;
    const show = (i, px) => {
      at = i;
      cross.setAttribute("x1", x(i));
      cross.setAttribute("x2", x(i));
      cross.setAttribute("opacity", 0.35);
      tip.replaceChildren();
      tip.append(el("b", {}, dayName(H.dates[i], { weekday: true, year: true })));
      const line = (label, v) => {
        const r = el("div", { class: "tip-row" });
        r.append(el("span", {}, label), el("span", {}, v));
        tip.append(r);
      };
      if (H.observed[i] != null) line(H.thin[i] ? "Measured (part day)" : "Measured", H.observed[i].toFixed(1));
      else if (H.dates[i] <= D.today) line("Measured", "not published");
      if (H.forecast[i] != null) line("Pawan", H.forecast[i].toFixed(1));
      else if (H.backtest[i] != null) line("Pawan, backtest", H.backtest[i].toFixed(1));
      if (H.low[i] != null) line("Likely range", `${Math.round(H.low[i])} to ${Math.round(H.high[i])}`);
      if (H.cams[i] != null) line("CAMS", H.cams[i].toFixed(1));
      tip.hidden = false;
      // px is in the frame's own pixels; keyboard moves have none,
      // so the day's position on the chart is converted instead.
      const r = root.getBoundingClientRect(), f = frame.getBoundingClientRect();
      const anchor = px != null ? px : r.left - f.left + x(i) * (r.width / W);
      const left = anchor + 14;
      tip.style.left = `${left + tip.offsetWidth > f.width ? anchor - tip.offsetWidth - 14 : left}px`;
      tip.style.top = "14px";
    };
    const hide = () => { tip.hidden = true; cross.setAttribute("opacity", 0); };
    const locate = (evt) => {
      const r = root.getBoundingClientRect();
      const px = (evt.clientX - r.left) * (W / r.width);
      const f = (px - m.l) / (W - m.l - m.r);
      const i = Math.round(idx[0] + f * (idx[idx.length - 1] - idx[0]));
      const fx = evt.clientX - frame.getBoundingClientRect().left;
      return [Math.min(Math.max(i, idx[0]), idx[idx.length - 1]), fx];
    };
    hit.addEventListener("pointermove", (e) => { const [i, px] = locate(e); show(i, px); });
    hit.addEventListener("pointerdown", (e) => { const [i, px] = locate(e); show(i, px); });
    hit.addEventListener("pointerleave", hide);
    // Keyboard read-out lives on the container, which is an
    // ordinary focusable element in every browser.
    box.tabIndex = 0;
    box.setAttribute("aria-label", "Chart read-out. Use the left and right arrow keys to move between days.");
    box.onblur = hide;
    box.onkeydown = (e) => {
      if (e.key !== "ArrowLeft" && e.key !== "ArrowRight") return;
      e.preventDefault();
      const next = (at == null ? idx[idx.length - 1] : at) + (e.key === "ArrowLeft" ? -1 : 1);
      show(Math.min(Math.max(next, idx[0]), idx[idx.length - 1]));
    };
  }

  // ---------------------------------------------------------------
  // track record

  function renderRecord() {
    const R = D.record || {};
    const parts = [];
    if (R.issued) {
      parts.push(`Pawan has issued ${R.issued} forecasts since ${dayName(R.first)}, each one frozen the morning it was made.`);
    }
    if (R.scored) {
      parts.push(`The station has since published a full day for ${R.scored} of them. Pawan put ${R.band_hits} in the right AQI band, and its typical miss was ${R.mae.toFixed(1)} \u00b5g/m\u00b3.`);
      if (R.persistence_mae != null) {
        parts.push(`Repeating the newest published reading, the simplest honest alternative, missed by ${R.persistence_mae.toFixed(1)} on the same days.`);
      }
      if (R.with_range) {
        parts.push(`The likely range held the measured value on ${R.in_range} of ${R.with_range} days.`);
      }
    } else if (R.issued) {
      parts.push("None has been checked yet: the station publishes a few days late.");
    }
    $("record-lede").textContent = parts.join(" ");

    const tiles = $("tiles");
    tiles.replaceChildren();
    const colour = (name) => (D.bands.find((b) => b.name === name) || {}).colour || "transparent";
    for (const r of D.recent || []) {
      const t = el("div", { class: "tile", role: "listitem" });
      const said = `${dayName(r.date, { weekday: true, short: true })}: forecast ${Math.round(r.pm25)} (${r.band})`;
      const got = r.actual != null ? `, measured ${Math.round(r.actual)} (${r.actual_band})` : ", not measured yet";
      t.title = said + got;
      t.setAttribute("aria-label", said + got);
      t.append(el("span", { style: `background:${colour(r.band)}` }));
      t.append(r.actual_band ? el("span", { style: `background:${colour(r.actual_band)}` }) : el("span", { class: "pending" }));
      tiles.append(t);
    }

    const B = D.backtest;
    if (B && B.days) {
      const pct = (v) => `${Math.round(v * 100)}%`;
      let text = `Over a backtest of ${B.days} days, ${dayName(B.first, { year: true })} to ${dayName(B.last, { year: true })}, ` +
        `with every forecast made only from the days before it, Pawan's typical miss was ${B.mae.toFixed(1)} \u00b5g/m\u00b3 ` +
        `against ${B.persistence_mae.toFixed(1)} for repeating the newest reading`;
      text += B.skill != null ? `, an error ${pct(B.skill)} smaller.` : ".";
      if (B.cams_mae != null) text += ` CAMS on its own missed by ${B.cams_mae.toFixed(1)}.`;
      const S = B.seasons || {};
      if (S.burning && S.calm) {
        text += ` The project set out to cut that error by ${pct(S.calm.target)} in the calm months and ${pct(S.burning.target)} in the burning season; ` +
          `the backtest shows ${pct(S.calm.skill)} and ${pct(S.burning.skill)}.`;
      }
      $("record-backtest").textContent = text;
    }
  }

  // ---------------------------------------------------------------
  // behind the scenes

  function renderHealth() {
    const h = D.health || {};
    const box = $("health");
    box.replaceChildren();
    const green = "#3a9a5b", amber = "#d29a1c", red = "#c8412e";
    const item = (label, text, dot) => {
      const dd = el("dd");
      if (dot) dd.append(el("span", { class: "status-dot", style: `background:${dot}` }));
      dd.append(text);
      box.append(el("dt", {}, label), dd);
    };

    const age = (Date.now() - Date.parse(D.generated_at)) / 3600000;
    item("Page rebuilt", stamp(D.generated_at), age < 30 ? green : amber);

    if (h.newest_obs) {
      const late = h.obs_age_days > h.stale_after_days ? red : h.obs_age_days > h.usual_age_days + 1 ? amber : green;
      item("Newest station reading",
        `${dayName(h.newest_obs)}, ${h.obs_age_days} days ago. The feed usually runs about ${h.usual_age_days} days behind.`, late);
    }
    if (h.issued) {
      const streak = h.streak > 0 ? `Every morning for the last ${h.streak} days` : "Not issued this morning";
      item("Forecasts issued", `${streak}; ${h.issued} in all since ${dayName(h.first_forecast)}.`, h.streak > 0 ? green : red);
    }
    item("Training data", `${h.usable_rows} usable days out of ${h.rows} on record, starting ${dayName(h.first_row, { year: true })}.`);
    item("Model", `Ridge regression on ${h.inputs} inputs, refitted from scratch and re-tested against every past day each morning.`);
    item("Checks", "The full test suite runs before each morning's data is committed.");

    $("foot-stamp").textContent = `Data generated ${stamp(D.generated_at)}.`;
  }

  // ---------------------------------------------------------------

  function fail(message) {
    $("hero-when").textContent = "The dashboard data could not be loaded.";
    const box = $("notice");
    box.replaceChildren(message + " The same forecast is on the ", el("a", { href: "../forecast/" }, "plain forecast page"), ".");
    box.hidden = false;
  }

  function start(data) {
    D = data;
    if (D.error) {
      fail(`This morning's data file was not built (${D.error}).`);
      return;
    }
    const parts = [renderHero, renderNotices, renderDrivers, renderRecord, renderHealth];
    if (D.history) {
      parts.push(() => {
        buildRanges();
        drawChart();
        if (window.ResizeObserver) {
          let last = 0;
          new ResizeObserver(() => {
            const w = $("chart").clientWidth;
            if (Math.abs(w - last) > 4) { last = w; drawChart(); }
          }).observe($("chart"));
        }
      });
    }
    // One broken section should not take the rest of the page down.
    for (const part of parts) {
      try { part(); } catch (err) { console.error(part.name || "section", err); }
    }
    // Leaflet is deferred like this script, but may still be on its
    // way; the map waits for the page's load event if it has to.
    const map = () => { try { renderFires(); } catch (err) { console.error("map", err); } };
    if (document.readyState === "complete") map(); else window.addEventListener("load", map, { once: true });
  }

  fetch("data.json", { cache: "no-cache" })
    .then((r) => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); })
    .then(start)
    .catch((err) => { console.error(err); fail(`The request for data.json failed (${err.message}).`); });
})();
