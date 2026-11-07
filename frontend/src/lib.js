// Shared constants and helpers. Contract: docs/api-contract.md

export const CORK_CENTRE = [51.8985, -8.4756];
export const CELL_SIZE_M = 350; // matches backend config.CELL_SIZE_M

export const BUSINESS_TYPES = [
  { value: "cafe", label: "Specialty café" },
  { value: "barber", label: "Barber" },
  { value: "gym", label: "Gym" },
  { value: "restaurant", label: "Restaurant or takeaway" },
  { value: "convenience", label: "Convenience store" },
];

export const CUSTOMERS = [
  { value: "students", label: "Students" },
  { value: "office_workers", label: "Office workers" },
  { value: "residents", label: "Local residents" },
  { value: "visitors", label: "Visitors and shoppers" },
];

export const BUDGETS = [
  { value: "tight", label: "Tight" },
  { value: "moderate", label: "Moderate" },
  { value: "flexible", label: "Flexible" },
];

export const METRICS = [
  { key: "total", label: "Overall", hint: "Weighted total for your brief" },
  { key: "demand", label: "Demand", hint: "Residents, students, offices and visitors nearby" },
  { key: "competition", label: "Competition", hint: "Higher means fewer rivals nearby" },
  { key: "access", label: "Access", hint: "Bus stops and shops nearby" },
  { key: "cost", label: "Cost", hint: "Distance-from-centre proxy for rent pressure" },
];

export const AGENTS = [
  { key: "demand", label: "Demand analyst", stage: "specialist" },
  { key: "competition", label: "Competition analyst", stage: "specialist" },
  { key: "access", label: "Access analyst", stage: "specialist" },
  { key: "cost", label: "Cost analyst", stage: "specialist" },
  { key: "challenger", label: "Challenger", stage: "challenger" },
  { key: "reporter", label: "Reporter", stage: "reporter" },
];

export const labelFor = (list, value) =>
  list.find((x) => x.value === value)?.label ?? value;

// ---- API ------------------------------------------------------------------

async function post(path, body, signal) {
  const res = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  });
  if (!res.ok) {
    let detail = "";
    try {
      detail = JSON.stringify((await res.json()).detail ?? "");
    } catch {
      /* ignore */
    }
    throw new Error(`${path} failed (${res.status}) ${detail}`.trim());
  }
  return res.json();
}

export const analyze = (brief, signal) => post("/api/analyze", brief, signal);
export const explain = (analysis, signal) => post("/api/explain", analysis, signal);

// ---- Colour ramps for the score map -----------------------------------------
// Dark theme: slate -> teal -> mint -> lime, bright on a dark base map.
// Light theme: pale mint -> teal -> deep blue, dark on a light base map.
// In both, a stronger score is a more prominent colour.

const RAMPS = {
  dark: [
    [0.0, [26, 46, 64]],
    [0.35, [24, 110, 120]],
    [0.7, [61, 214, 181]],
    [1.0, [214, 245, 110]],
  ],
  light: [
    [0.0, [206, 236, 226]],
    [0.35, [95, 190, 168]],
    [0.7, [20, 128, 112]],
    [1.0, [12, 52, 92]],
  ],
};

export function rampRGB(t, theme = "dark") {
  const stops = RAMPS[theme] ?? RAMPS.dark;
  const x = Math.max(0, Math.min(1, t));
  for (let i = 1; i < stops.length; i++) {
    const [t1, c1] = stops[i];
    const [t0, c0] = stops[i - 1];
    if (x <= t1) {
      const f = (x - t0) / (t1 - t0 || 1);
      return c0.map((v, k) => Math.round(v + (c1[k] - v) * f));
    }
  }
  return stops[stops.length - 1][1];
}

export const rampCSS = (t, theme) => `rgb(${rampRGB(t, theme).join(",")})`;

export const rampGradient = (theme = "dark") =>
  `linear-gradient(90deg, ${(RAMPS[theme] ?? RAMPS.dark)
    .map(([t, c]) => `rgb(${c.join(",")}) ${t * 100}%`)
    .join(", ")})`;

// ---- Zoom-dependent aggregation ---------------------------------------------
// Zoomed out, nearby grid cells are grouped into one circle showing their
// average scores; zoomed in, every ~350 m cell is its own circle.

export function groupSizeForZoom(zoom) {
  if (zoom <= 12) return 4; // ~1.4 km groups
  if (zoom === 13) return 2; // ~700 m groups
  return 1; // single cells
}

const GRID_ORIGIN = [51.86, -8.56]; // matches the backend bbox corner

export function aggregateCells(cells, k) {
  const keys = ["total", "demand", "competition", "access", "cost"];
  if (k <= 1) {
    return cells.map((c) => ({
      id: c.id, lat: c.lat, lng: c.lng, n: 1, scores: c.scores, best: c.scores.total, members: [c],
    }));
  }
  const stepLat = (k * CELL_SIZE_M) / 111320;
  const stepLng = (k * CELL_SIZE_M) / (111320 * Math.cos((GRID_ORIGIN[0] * Math.PI) / 180));
  const groups = new Map();
  for (const c of cells) {
    const row = Math.floor((c.lat - GRID_ORIGIN[0]) / stepLat);
    const col = Math.floor((c.lng - GRID_ORIGIN[1]) / stepLng);
    const key = `${row}:${col}`;
    let g = groups.get(key);
    if (!g) {
      g = { id: `g${k}-${key}`, row, col, n: 0, members: [], sums: Object.fromEntries(keys.map((x) => [x, 0])), best: -Infinity };
      groups.set(key, g);
    }
    g.n += 1;
    g.members.push(c);
    keys.forEach((x) => (g.sums[x] += c.scores[x]));
    g.best = Math.max(g.best, c.scores.total);
  }
  // Circles sit at the centre of their block, so neighbours never overlap.
  return [...groups.values()].map((g) => ({
    id: g.id,
    lat: GRID_ORIGIN[0] + (g.row + 0.5) * stepLat,
    lng: GRID_ORIGIN[1] + (g.col + 0.5) * stepLng,
    n: g.n,
    best: g.best,
    members: g.members,
    scores: Object.fromEntries(keys.map((x) => [x, Math.round(g.sums[x] / g.n)])),
  }));
}

// Half a cell in degrees, so a centre point becomes a square.
export function cellBounds(lat, lng) {
  const half = CELL_SIZE_M / 2;
  const dLat = half / 111320;
  const dLng = half / (111320 * Math.cos((lat * Math.PI) / 180));
  return [
    [lat - dLat, lng - dLng],
    [lat + dLat, lng + dLng],
  ];
}

// ---- Approximate area names -------------------------------------------------
// The API returns grid ids (e.g. r9c4), so the UI labels each pick with the
// nearest well-known Cork neighbourhood. Approximate centres, labels only:
// no score depends on them.

const AREAS = [
  ["City centre", 51.8985, -8.4756],
  ["Shandon", 51.903, -8.477],
  ["Sunday's Well", 51.9017, -8.4935],
  ["Gurranabraher", 51.9065, -8.4955],
  ["Fairhill", 51.915, -8.48],
  ["Blackpool", 51.914, -8.468],
  ["Mayfield", 51.913, -8.44],
  ["Montenotte", 51.904, -8.456],
  ["Knocknaheeny", 51.913, -8.513],
  ["UCC", 51.8935, -8.4919],
  ["Victoria Cross", 51.8955, -8.505],
  ["Glasheen", 51.889, -8.505],
  ["Wilton", 51.884, -8.512],
  ["Bishopstown", 51.882, -8.522],
  ["Model Farm Road", 51.889, -8.528],
  ["Togher", 51.875, -8.49],
  ["Ballyphehane", 51.882, -8.481],
  ["Turners Cross", 51.886, -8.469],
  ["Ballintemple", 51.893, -8.43],
  ["Ballinlough", 51.889, -8.43],
  ["Blackrock", 51.8996, -8.4019],
  ["Mahon", 51.887, -8.395],
  ["Douglas", 51.877, -8.436],
  ["Frankfield", 51.865, -8.47],
  ["Docklands", 51.8995, -8.455],
];

export function metresBetween(lat1, lng1, lat2, lng2) {
  const kx = 111320 * Math.cos((lat1 * Math.PI) / 180);
  return Math.hypot((lng2 - lng1) * kx, (lat2 - lat1) * 111320);
}

function nearestAreaEntry(lat, lng) {
  let best = AREAS[0];
  let bestD = Infinity;
  for (const a of AREAS) {
    const d = metresBetween(lat, lng, a[1], a[2]);
    if (d < bestD) {
      bestD = d;
      best = a;
    }
  }
  return best;
}

export const nearestArea = (lat, lng) => nearestAreaEntry(lat, lng)[0];

const COMPASS = ["north", "north-east", "east", "south-east", "south", "south-west", "west", "north-west"];

// cell_id -> display name for the shortlist. Two picks near the same
// neighbourhood get a direction so they stay distinguishable.
export function pickLabels(picks) {
  const names = picks.map((p) => nearestAreaEntry(p.lat, p.lng));
  const counts = {};
  names.forEach((a) => (counts[a[0]] = (counts[a[0]] ?? 0) + 1));
  const out = {};
  picks.forEach((p, i) => {
    const [name, alat, alng] = names[i];
    if (counts[name] === 1) {
      out[p.cell_id] = name;
      return;
    }
    const dy = (p.lat - alat) * 111320;
    const dx = (p.lng - alng) * 111320 * Math.cos((p.lat * Math.PI) / 180);
    const deg = ((Math.atan2(dx, dy) * 180) / Math.PI + 360) % 360;
    out[p.cell_id] = `${name} (${COMPASS[Math.round(deg / 45) % 8]})`;
  });
  return out;
}

// ---- Formatting -------------------------------------------------------------

export function fmt(v, metric) {
  if (v === null || v === undefined || Number.isNaN(v)) return "–";
  if (metric === "distance_centre_km") return v.toFixed(1);
  return Math.round(v).toLocaleString("en-IE");
}

// Which direction is good for an evidence row: 1 higher, -1 lower, 0 neutral.
export const GOOD_DIRECTION = {
  residents_600m: 1,
  offices_500m: 1,
  bus_stops_400m: 1,
  competitors_400m: -1,
  distance_centre_km: 0,
};
