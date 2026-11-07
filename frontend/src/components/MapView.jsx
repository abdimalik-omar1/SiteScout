import { useEffect, useMemo, useRef, useState } from "react";
import L from "leaflet";
import {
  Circle,
  MapContainer,
  Marker,
  Pane,
  TileLayer,
  Tooltip,
  useMap,
  useMapEvents,
  ZoomControl,
} from "react-leaflet";
import {
  CELL_SIZE_M,
  CORK_CENTRE,
  METRICS,
  aggregateCells,
  groupSizeForZoom,
  nearestArea,
  rampCSS,
  rampGradient,
} from "../lib.js";

// Set VITE_CARTO_API_KEY in frontend/.env for CARTO basemaps.
const CARTO_KEY = (import.meta.env.VITE_CARTO_API_KEY ?? "").trim();

const RING = {
  dark: { inner: "#3dd6b5", outer: "#93a0b2" },
  light: { inner: "#0f7f6c", outer: "#6f7a72" },
};

function Basemap({ theme }) {
  const osm = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';
  if (CARTO_KEY) {
    const style = theme === "light" ? "light_all" : "dark_all";
    // Same tile address the team committed in 370f2a1, with the style swapped per theme.
    return (
      <TileLayer
        key={`carto-${style}`}
        url={`https://{s}.basemaps.cartocdn.com/${style}/{z}/{x}/{y}{r}.png?key=${encodeURIComponent(CARTO_KEY)}`}
        attribution={`${osm} &copy; <a href="https://carto.com/attributions">CARTO</a>`}
        subdomains="abcd"
        maxZoom={19}
      />
    );
  }
  // No CARTO key: standard OpenStreetMap tiles, darkened with CSS in dark mode.
  return (
    <TileLayer
      key={`osm-${theme}`}
      className={theme === "dark" ? "tiles-dark" : ""}
      url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
      attribution={osm}
      maxZoom={19}
    />
  );
}

// Tracks the zoom level so the circles can regroup.
function ZoomWatcher({ onZoom }) {
  const map = useMapEvents({ zoomend: () => onZoom(map.getZoom()) });
  useEffect(() => onZoom(map.getZoom()), [map, onZoom]);
  return null;
}

// The heat pane is blurred so overlapping circles melt into a smooth surface.
// Blur grows with the circle size on screen, so it looks the same at every zoom.
function HeatBlur({ k }) {
  const map = useMap();
  useEffect(() => {
    const apply = () => {
      const pane = map.getPane("heat");
      if (!pane) return;
      const mPerPx = (156543.03 * Math.cos((map.getCenter().lat * Math.PI) / 180)) / 2 ** map.getZoom();
      const radiusPx = (k * CELL_SIZE_M * 0.8) / mPerPx;
      const blur = Math.max(6, Math.min(36, radiusPx * 0.45));
      pane.style.filter = `blur(${blur.toFixed(1)}px)`;
    };
    apply();
    map.on("zoomend", apply);
    return () => map.off("zoomend", apply);
  }, [map, k]);
  return null;
}

// Heatmap of grouped cells. Zoomed out, each circle averages a block of
// nearby ~350 m cells; zoomed in, each cell is its own circle. Circles
// overlap and the pane is blurred, so scores blend into a smooth surface.
function ScoreLayer({ groups, metric, range, k, theme }) {
  const radius = k * CELL_SIZE_M * 0.8;
  // Own canvas with a wide margin past the screen edge. The blur softens the
  // canvas edge too, so with the default small margin a soft band showed at
  // the top while dragging, until the map redrew.
  const renderer = useMemo(() => L.canvas({ pane: "heat", padding: 0.6 }), []);
  return groups.map((g) => {
    const v = g.scores[metric];
    const t = range.max > range.min ? (v - range.min) / (range.max - range.min) : 1;
    return (
      <Circle
        key={g.id}
        center={[g.lat, g.lng]}
        radius={radius}
        renderer={renderer}
        pathOptions={{
          stroke: false,
          fillColor: rampCSS(t, theme),
          fillOpacity: 0.04 + 0.66 * Math.pow(t, 1.8),
        }}
      >
        <Tooltip className="cell-tip" sticky direction="top" offset={[0, -6]}>
          <div>
            <strong>Near {nearestArea(g.lat, g.lng)}</strong>
            <div className="tip-sub">
              {g.n > 1 ? `Average of ${g.n} areas · best overall ${g.best}` : "Single ~350 m area"}
            </div>
            <div className="tip-grid">
              <span>Overall</span><b>{g.scores.total}</b>
              <span>Demand</span><b>{g.scores.demand}</b>
              <span>Competition</span><b>{g.scores.competition}</b>
              <span>Access</span><b>{g.scores.access}</b>
              <span>Cost</span><b>{g.scores.cost}</b>
            </div>
          </div>
        </Tooltip>
      </Circle>
    );
  });
}

function pinIcon(rank, selected) {
  return L.divIcon({
    className: "",
    html: `<div class="pin${rank === 1 ? " first" : ""}${selected ? " selected" : ""}">${rank}</div>`,
    iconSize: [30, 30],
    iconAnchor: [15, 15],
  });
}

// A new analysis shows the whole city; picking a location afterwards flies to it.
function Camera({ analysis, selected }) {
  const map = useMap();
  const shownFor = useRef(null);

  useEffect(() => {
    if (!analysis) return;
    if (shownFor.current !== analysis) {
      shownFor.current = analysis;
      const pts = (analysis.cells.length > 5 ? analysis.cells : analysis.shortlist).map((c) => [c.lat, c.lng]);
      if (pts.length) map.flyToBounds(L.latLngBounds(pts).pad(0.04), { duration: 0.8 });
      return;
    }
    if (selected) map.flyTo([selected.lat, selected.lng], Math.max(map.getZoom(), 14), { duration: 0.8 });
  }, [analysis, selected?.cell_id, map]); // eslint-disable-line react-hooks/exhaustive-deps

  return null;
}

const LEVEL_TEXT = {
  4: "Heat shows averages over about 1.4 km blocks. Zoom in for detail.",
  2: "Heat shows averages over about 700 m blocks. Zoom in for detail.",
  1: "Heat at the finest level: each ~350 m area.",
};

export default function MapView({ analysis, labels, selectedRank, onSelect, metric, onMetric, loading, theme }) {
  const [zoom, setZoom] = useState(13);
  const k = groupSizeForZoom(zoom);
  const selected = analysis?.shortlist.find((p) => p.rank === selectedRank) ?? null;
  const metricInfo = METRICS.find((m) => m.key === metric);
  const ring = RING[theme] ?? RING.dark;

  // Sample mode has only five cells, so grouping would hide them.
  const level = analysis && analysis.cells.length > 5 ? k : 1;
  const groups = useMemo(
    () => (analysis ? aggregateCells(analysis.cells, level) : []),
    [analysis, level]
  );
  const range = useMemo(() => {
    if (!groups.length) return null;
    const vals = groups.map((g) => g.scores[metric]);
    return { min: Math.min(...vals), max: Math.max(...vals) };
  }, [groups, metric]);

  return (
    <div className="map-wrap">
      <MapContainer
        center={CORK_CENTRE}
        zoom={13}
        minZoom={11}
        preferCanvas
        zoomControl={false}
        style={{ height: "100%", width: "100%" }}
      >
        <Basemap theme={theme} />
        <ZoomControl position="bottomright" />
        <ZoomWatcher onZoom={setZoom} />
        <Pane name="heat" style={{ zIndex: 350 }}>
          {range && <ScoreLayer groups={groups} metric={metric} range={range} k={level} theme={theme} />}
        </Pane>
        <HeatBlur k={level} />

        {selected && (
          <Pane name="rings" style={{ zIndex: 450, pointerEvents: "none" }}>
            <Circle
              center={[selected.lat, selected.lng]}
              radius={600}
              interactive={false}
              pathOptions={{ color: ring.outer, weight: 1.2, dashArray: "4 6", fill: false }}
            />
            <Circle
              center={[selected.lat, selected.lng]}
              radius={400}
              interactive={false}
              pathOptions={{ color: ring.inner, weight: 1.8, dashArray: "6 6", fillColor: ring.inner, fillOpacity: 0.05 }}
            />
          </Pane>
        )}

        {analysis?.shortlist.map((p) => (
          <Marker
            key={p.cell_id}
            position={[p.lat, p.lng]}
            icon={pinIcon(p.rank, p.rank === selectedRank)}
            zIndexOffset={p.rank === selectedRank ? 1000 : 500 - p.rank}
            eventHandlers={{ click: () => onSelect(p.rank) }}
            keyboard
          >
            <Tooltip className="cell-tip" direction="top" offset={[0, -16]}>
              <div>
                <strong>#{p.rank} · {labels?.[p.cell_id] ?? nearestArea(p.lat, p.lng)}</strong>
                <div className="tip-sub">Shortlisted pick · click for details</div>
                <div className="tip-grid">
                  <span>Overall</span><b>{p.scores.total}</b>
                  <span>Demand</span><b>{p.scores.demand}</b>
                  <span>Competition</span><b>{p.scores.competition}</b>
                  <span>Access</span><b>{p.scores.access}</b>
                  <span>Cost</span><b>{p.scores.cost}</b>
                </div>
              </div>
            </Tooltip>
          </Marker>
        ))}

        <Camera analysis={analysis} selected={selected} />
      </MapContainer>

      <div className="map-top">
        {analysis ? (
          <div className="overlay metric-switch" role="group" aria-label="Colour the map by">
            {METRICS.map((m) => (
              <button
                key={m.key}
                type="button"
                aria-pressed={metric === m.key}
                title={m.hint}
                onClick={() => onMetric(m.key)}
              >
                {m.label}
              </button>
            ))}
          </div>
        ) : <span />}
      </div>

      {loading && (
        <div className="overlay map-loading" role="status">
          <span className="dot dot-running" /> Scoring every Cork cell…
        </div>
      )}

      {analysis && range && (
        <div className="overlay legend">
          <div className="small" style={{ fontWeight: 600 }}>
            {metricInfo.label} score{level > 1 ? " (area average)" : ""}
          </div>
          <div className="small muted">{metricInfo.hint}</div>
          <div className="legend-bar" style={{ background: rampGradient(theme) }} />
          <div className="legend-scale">
            <span>{range.min} weaker</span>
            <span>stronger {range.max}</span>
          </div>
          <div className="legend-level small muted" aria-live="polite">{LEVEL_TEXT[level]}</div>
          {selected && (
            <div className="legend-key">
              <span>
                <svg width="18" height="8" aria-hidden="true"><line x1="0" y1="4" x2="18" y2="4" stroke={ring.inner} strokeWidth="2" strokeDasharray="4 3" /></svg>
                400 m competitors
              </span>
              <span>
                <svg width="18" height="8" aria-hidden="true"><line x1="0" y1="4" x2="18" y2="4" stroke={ring.outer} strokeWidth="1.5" strokeDasharray="3 4" /></svg>
                600 m residents
              </span>
            </div>
          )}
        </div>
      )}

      {!analysis && !loading && (
        <div className="map-empty">
          <div className="overlay">
            <div style={{ fontFamily: "var(--display)", fontSize: 19, fontWeight: 600, marginBottom: 6 }}>
              Scout Cork to light up the map
            </div>
            <div className="muted small">
              Every 350 m area of the city is scored against your brief. Zoom out to see neighbourhood averages, zoom in for the detail.
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
