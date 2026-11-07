import { useEffect, useMemo, useRef } from "react";
import L from "leaflet";
import {
  Circle,
  MapContainer,
  Marker,
  Rectangle,
  TileLayer,
  Tooltip,
  useMap,
} from "react-leaflet";
import {
  CORK_CENTRE,
  METRICS,
  RAMP_GRADIENT,
  cellBounds,
  nearestArea,
  rampCSS,
} from "../lib.js";

// One square per ~350 m grid cell, coloured by the chosen score.
// The colour is stretched over the min..max of that score in this analysis,
// and weaker cells fade out so the strong areas stand out on the dark map.
function ScoreLayer({ cells, metric }) {
  const range = useMemo(() => {
    const vals = cells.map((c) => c.scores[metric]);
    return { min: Math.min(...vals), max: Math.max(...vals) };
  }, [cells, metric]);

  return cells.map((c) => {
    const v = c.scores[metric];
    const t = range.max > range.min ? (v - range.min) / (range.max - range.min) : 1;
    const opacity = 0.03 + 0.7 * Math.pow(t, 2.2);
    return (
      <Rectangle
        key={c.id}
        bounds={cellBounds(c.lat, c.lng)}
        pathOptions={{
          stroke: false,
          fillColor: rampCSS(t),
          fillOpacity: opacity,
        }}
      >
        <Tooltip className="cell-tip" sticky direction="top" offset={[0, -6]}>
          <div>
            <strong>Near {nearestArea(c.lat, c.lng)}</strong>
            <div className="tip-grid">
              <span>Overall</span><b>{c.scores.total}</b>
              <span>Demand</span><b>{c.scores.demand}</b>
              <span>Competition</span><b>{c.scores.competition}</b>
              <span>Access</span><b>{c.scores.access}</b>
              <span>Cost</span><b>{c.scores.cost}</b>
            </div>
          </div>
        </Tooltip>
      </Rectangle>
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

export default function MapView({ analysis, labels, selectedRank, onSelect, metric, onMetric, loading }) {
  const selected = analysis?.shortlist.find((p) => p.rank === selectedRank) ?? null;
  const metricInfo = METRICS.find((m) => m.key === metric);
  const range = useMemo(() => {
    if (!analysis?.cells.length) return null;
    const vals = analysis.cells.map((c) => c.scores[metric]);
    return { min: Math.min(...vals), max: Math.max(...vals) };
  }, [analysis, metric]);

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
        <TileLayer
          url={`https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png?key=${encodeURIComponent(import.meta.env.VITE_CARTO_API_KEY ?? "")}`}
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
          subdomains="abcd"
          maxZoom={19}
        />
        {analysis && <ScoreLayer cells={analysis.cells} metric={metric} />}

        {selected && (
          <>
            <Circle
              center={[selected.lat, selected.lng]}
              radius={600}
              pathOptions={{ color: "#93a0b2", weight: 1.2, dashArray: "4 6", fill: false }}
            />
            <Circle
              center={[selected.lat, selected.lng]}
              radius={400}
              pathOptions={{ color: "#3dd6b5", weight: 1.6, dashArray: "6 6", fillColor: "#3dd6b5", fillOpacity: 0.05 }}
            />
          </>
        )}

        {analysis?.shortlist.map((p) => (
          <Marker
            key={p.cell_id}
            position={[p.lat, p.lng]}
            icon={pinIcon(p.rank, p.rank === selectedRank)}
            zIndexOffset={p.rank === selectedRank ? 1000 : 500 - p.rank}
            eventHandlers={{ click: () => onSelect(p.rank) }}
            keyboard
            title={`Pick ${p.rank}: near ${labels?.[p.cell_id] ?? nearestArea(p.lat, p.lng)}, score ${p.scores.total}`}
          />
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
            {metricInfo.label} score
          </div>
          <div className="small muted">{metricInfo.hint}</div>
          <div className="legend-bar" style={{ background: RAMP_GRADIENT }} />
          <div className="legend-scale">
            <span>{range.min} weaker</span>
            <span>stronger {range.max}</span>
          </div>
          {selected && (
            <div className="legend-key">
              <span>
                <svg width="18" height="8" aria-hidden="true"><line x1="0" y1="4" x2="18" y2="4" stroke="#3dd6b5" strokeWidth="2" strokeDasharray="4 3" /></svg>
                400 m competitors
              </span>
              <span>
                <svg width="18" height="8" aria-hidden="true"><line x1="0" y1="4" x2="18" y2="4" stroke="#93a0b2" strokeWidth="1.5" strokeDasharray="3 4" /></svg>
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
              Every 350 m square of the city is scored against your brief. The best areas glow; the top five get numbered pins.
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
