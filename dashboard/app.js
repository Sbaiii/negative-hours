// Negative Hours dashboard: reads data/dashboard.json (written daily by the
// refresh workflow) and renders KPI tiles, the latest price curve and a table.
// Vanilla JS, no build step; the chart is inline SVG.

"use strict";

const DEFAULT_ZONE = "DE_LU";
const SVG_NS = "http://www.w3.org/2000/svg";

const fmt = {
  hours: (v) => v.toLocaleString("en-GB", { maximumFractionDigits: 2 }) + " h",
  euro: (v) => "€" + Math.round(v).toLocaleString("en-GB"),
  percent: (v) => (v * 100).toFixed(1) + "%",
  price: (v) => (v < 0 ? "−" : "") + Math.abs(v).toFixed(2),
  date: (iso) =>
    new Date(iso + "T12:00:00Z").toLocaleDateString("en-GB", {
      day: "numeric", month: "long", year: "numeric", timeZone: "UTC",
    }),
  shortDate: (iso) =>
    new Date(iso + "T12:00:00Z").toLocaleDateString("en-GB", {
      day: "numeric", month: "short", timeZone: "UTC",
    }),
};

// What each tile shows, and how to compare this year with last year.
const KPIS = [
  {
    key: "negative_hours",
    title: "Negative-price hours",
    format: fmt.hours,
    change: "relative",
    note: "Hours whose hourly mean day-ahead price was below 0.",
  },
  {
    key: "solar_capture_rate",
    title: "Solar capture rate",
    format: fmt.percent,
    change: "points",
    note: "What solar earned, as a share of the average price.",
  },
  {
    key: "battery_revenue_eur_per_mw",
    title: "Battery revenue per MW",
    format: fmt.euro,
    change: "relative",
    note: "2-hour battery, day-ahead only, perfect foresight: an upper bound.",
  },
  {
    key: "ev_smart_saving_eur",
    title: "EV smart-charging saving",
    format: (v) => fmt.euro(v),
    change: "relative",
    note: "Per car vs charging at 18:00, wholesale price only.",
    extra: (p) => (p.ev_smart_saving_share == null ? "" : ` (${fmt.percent(p.ev_smart_saving_share)} of the cost)`),
  },
];

let data = null;

function el(tag, attrs = {}, text) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
  if (text !== undefined) node.textContent = text;
  return node;
}

function svg(tag, attrs = {}, text) {
  const node = document.createElementNS(SVG_NS, tag);
  for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
  if (text !== undefined) node.textContent = text;
  return node;
}

function changeText(kpi, current, previous) {
  if (current == null || previous == null) return "";
  if (kpi.change === "points") {
    const pts = (current - previous) * 100;
    return `${pts >= 0 ? "+" : "−"}${Math.abs(pts).toFixed(1)} points`;
  }
  if (previous === 0) return current === 0 ? "no change" : "new this year";
  const pct = (current / previous - 1) * 100;
  return `${pct >= 0 ? "+" : "−"}${Math.abs(pct).toFixed(0)}%`;
}

// Zones whose figures partly reflect a market rule rather than the generation mix.
const ZONE_NOTES = {
  IT_NORD:
    "North Italy: the Italian day-ahead market does not accept offers below 0 €/MWh, so prices " +
    "cannot go negative. Its negative hours (always 0), battery and EV figures partly reflect " +
    "that market rule.",
};

function renderKpis(zone) {
  const note = document.getElementById("zone-note");
  note.hidden = !ZONE_NOTES[zone.code];
  note.textContent = ZONE_NOTES[zone.code] || "";
  const { current, previous } = zone.kpis;
  document.getElementById("kpi-period").textContent =
    `${zone.name}, 1 January to ${fmt.date(current.last_day)}, compared with the same dates in ${previous.last_day.slice(0, 4)}.`;
  const box = document.getElementById("kpis");
  box.replaceChildren();
  for (const kpi of KPIS) {
    const tile = el("article", { class: "tile" });
    tile.append(el("h3", {}, kpi.title));
    const now = current[kpi.key];
    const before = previous[kpi.key];
    tile.append(el("p", { class: "value" }, now == null ? "n/a" : kpi.format(now)));
    const compare = el("p", { class: "compare" });
    if (before != null) {
      compare.textContent = `${previous.last_day.slice(0, 4)}: ${kpi.format(before)}`;
      const change = changeText(kpi, now, before);
      if (change) compare.append(" · ", el("strong", {}, change));
    }
    tile.append(compare);
    tile.append(el("p", { class: "note" }, kpi.note + (kpi.extra ? kpi.extra(current) : "")));
    box.append(tile);
  }
}

function niceStep(range, targetTicks) {
  const raw = range / targetTicks;
  const power = 10 ** Math.floor(Math.log10(raw));
  const unit = [1, 2, 2.5, 5, 10].find((m) => m * power >= raw);
  return unit * power;
}

function renderCurve(zone) {
  const { date, resolution_minutes: res, points } = zone.prices;
  const prices = points.map((p) => p[1]);
  const minP = Math.min(...prices);
  const maxP = Math.max(...prices);
  const minAt = points[prices.indexOf(minP)][0];
  const maxAt = points[prices.indexOf(maxP)][0];
  document.getElementById("curve-subtitle").textContent =
    `${zone.name}, ${fmt.date(date)}, ${res}-minute periods. ` +
    `Lowest ${fmt.price(minP)} €/MWh at ${minAt}, highest ${fmt.price(maxP)} €/MWh at ${maxAt}.`;

  const box = document.getElementById("curve");
  const width = Math.max(box.clientWidth, 300);
  const narrow = width < 520;
  const height = narrow ? 240 : 300;
  const m = { top: 16, right: 12, bottom: 30, left: narrow ? 44 : 52 };
  const plotW = width - m.left - m.right;
  const plotH = height - m.top - m.bottom;

  // Y scale always includes 0, so negative prices show below the zero line.
  const lo = Math.min(0, minP);
  const hi = Math.max(0, maxP);
  const step = niceStep(hi - lo || 1, 4);
  const yMin = Math.floor(lo / step) * step;
  const yMax = Math.ceil(hi / step) * step;
  const minutes = (t) => Number(t.slice(0, 2)) * 60 + Number(t.slice(3, 5));
  const dayMinutes = minutes(points[points.length - 1][0]) + res;
  const x = (min) => m.left + (min / dayMinutes) * plotW;
  const y = (p) => m.top + ((yMax - p) / (yMax - yMin)) * plotH;

  const root = svg("svg", {
    viewBox: `0 0 ${width} ${height}`,
    role: "img",
    "aria-label": `Day-ahead prices for ${zone.name} on ${fmt.date(date)}: from ${fmt.price(minP)} to ${fmt.price(maxP)} euros per MWh.`,
  });
  const style = getComputedStyle(document.documentElement);
  const token = (name) => style.getPropertyValue(name).trim();

  for (let v = yMin; v <= yMax + 1e-9; v += step) {
    root.append(svg("line", {
      x1: m.left, x2: width - m.right, y1: y(v), y2: y(v),
      stroke: v === 0 ? token("--ink-muted") : token("--grid"), "stroke-width": 1,
    }));
    root.append(svg("text", {
      x: m.left - 6, y: y(v) + 4, "text-anchor": "end", "font-size": 12, fill: token("--ink-secondary"),
    }, `${v < 0 ? "−" : ""}€${Math.abs(v)}`));
  }
  const tickEvery = narrow ? 6 : 3;
  for (let h = 0; h <= 24; h += tickEvery) {
    root.append(svg("text", {
      x: x(h * 60), y: height - 8, "text-anchor": h === 0 ? "start" : h === 24 ? "end" : "middle",
      "font-size": 12, fill: token("--ink-secondary"),
    }, `${String(h).padStart(2, "0")}:00`));
  }

  // Step line: each price holds for its whole period.
  let d = "";
  points.forEach(([t, p], i) => {
    const x0 = x(minutes(t));
    const x1 = x(minutes(t) + res);
    d += `${i === 0 ? "M" : "L"}${x0.toFixed(1)},${y(p).toFixed(1)}L${x1.toFixed(1)},${y(p).toFixed(1)}`;
  });
  root.append(svg("path", {
    d, fill: "none", stroke: zone.color, "stroke-width": 2, "stroke-linejoin": "round",
  }));
  box.replaceChildren(root);

  const table = document.getElementById("curve-table");
  table.replaceChildren();
  const head = el("thead");
  const headRow = el("tr");
  headRow.append(el("th", { scope: "col" }, "Local time"), el("th", { scope: "col" }, "€/MWh"));
  head.append(headRow);
  const body = el("tbody");
  for (const [t, p] of points) {
    const row = el("tr");
    row.append(el("td", {}, t), el("td", {}, fmt.price(p)));
    body.append(row);
  }
  table.append(el("caption", { class: "muted" }, `${zone.name}, ${fmt.date(date)}`), head, body);
}

function renderAllZones(selected) {
  const table = document.getElementById("all-zones");
  table.replaceChildren();
  const head = el("thead");
  const headRow = el("tr");
  for (const label of ["Zone", "To date", "Negative hours", "Solar capture rate", "Battery €/MW", "EV saving"]) {
    headRow.append(el("th", { scope: "col" }, label));
  }
  head.append(headRow);
  const body = el("tbody");
  for (const zone of data.zones) {
    const c = zone.kpis.current;
    const row = el("tr", zone.code === selected ? { class: "selected" } : {});
    const name = el("td");
    name.append(
      el("span", { class: "swatch", style: `background:${zone.color}`, "aria-hidden": "true" }),
      `${zone.name} (${zone.code})${ZONE_NOTES[zone.code] ? " *" : ""}`,
    );
    row.append(
      name,
      el("td", {}, fmt.shortDate(c.last_day)),
      el("td", {}, fmt.hours(c.negative_hours)),
      el("td", {}, c.solar_capture_rate == null ? "n/a" : fmt.percent(c.solar_capture_rate)),
      el("td", {}, fmt.euro(c.battery_revenue_eur_per_mw)),
      el("td", {}, fmt.euro(c.ev_smart_saving_eur)),
    );
    body.append(row);
  }
  table.append(head, body);
}

function selectZone(code) {
  const zone = data.zones.find((z) => z.code === code) || data.zones.find((z) => z.code === DEFAULT_ZONE);
  document.getElementById("zone-select").value = zone.code;
  history.replaceState(null, "", "#" + zone.code);
  renderKpis(zone);
  renderCurve(zone);
  renderAllZones(zone.code);
}

function setupTheme() {
  const button = document.getElementById("theme-toggle");
  const root = document.documentElement;
  const systemDark = window.matchMedia("(prefers-color-scheme: dark)");
  let saved = null;
  try { saved = localStorage.getItem("theme"); } catch (e) { /* storage blocked */ }
  if (saved) root.dataset.theme = saved;
  const isDark = () => (root.dataset.theme || (systemDark.matches ? "dark" : "light")) === "dark";
  const label = () => {
    button.textContent = isDark() ? "Light" : "Dark";
    button.setAttribute("aria-label", `Switch to ${isDark() ? "light" : "dark"} theme`);
  };
  button.addEventListener("click", () => {
    root.dataset.theme = isDark() ? "light" : "dark";
    try { localStorage.setItem("theme", root.dataset.theme); } catch (e) { /* storage blocked */ }
    label();
    if (data) selectZone(document.getElementById("zone-select").value);  // redraw SVG colours
  });
  systemDark.addEventListener("change", () => { label(); if (data) selectZone(document.getElementById("zone-select").value); });
  label();
}

async function main() {
  setupTheme();
  try {
    const response = await fetch("data/dashboard.json", { cache: "no-cache" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    data = await response.json();
  } catch (error) {
    document.getElementById("status").textContent = `Could not load the data (${error.message}).`;
    return;
  }
  document.getElementById("updated").textContent = fmt.date(data.generated_on);
  document.getElementById("updated").setAttribute("datetime", data.generated_on);
  document.getElementById("as-of").textContent = fmt.date(data.as_of_date);
  document.getElementById("as-of").setAttribute("datetime", data.as_of_date);

  const select = document.getElementById("zone-select");
  for (const zone of data.zones) select.append(el("option", { value: zone.code }, `${zone.name} (${zone.code})`));
  select.addEventListener("change", () => selectZone(select.value));
  selectZone(location.hash.slice(1) || DEFAULT_ZONE);

  let resizeTimer;
  window.addEventListener("resize", () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => selectZone(select.value), 150);
  });
}

main();
