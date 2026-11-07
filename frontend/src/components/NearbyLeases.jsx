import listings from "../data/commercial_leases.json";
import { nearestArea } from "../lib.js";

export function distanceKm(a, b) {
  const rad = Math.PI / 180;
  const dLat = (b.lat - a.lat) * rad;
  const dLng = (b.lng - a.lng) * rad;
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(a.lat * rad) * Math.cos(b.lat * rad) * Math.sin(dLng / 2) ** 2;
  return 6371 * 2 * Math.asin(Math.sqrt(Math.min(1, h)));
}

export function nearbyLeases(area, radius) {
  return area ? listings
    .map((listing) => ({ ...listing, distance: distanceKm(area, listing) }))
    .filter((listing) => listing.distance <= radius)
    .sort((a, b) => a.distance - b.distance) : [];
}

export default function NearbyLeases({ area, nearby, radius, onRadius }) {
  return (
    <section className="card card-pad leases" aria-labelledby="leases-heading">
      <h2 id="leases-heading" className="h2">Properties to lease near pick {area?.rank}</h2>
      {!area ? <p className="muted">Select a numbered point (1–5) to see nearby properties.</p> : <>
        <p>Pick {area.rank} · Near {nearestArea(area.lat, area.lng)}</p>
        <label className="field">Search radius
          <select className="select" value={radius} onChange={(event) => onRadius(Number(event.target.value))}>
            {[1, 3, 5].map((km) => <option key={km} value={km}>{km} km</option>)}
          </select>
        </label>
        <p className="small muted" role="status">{nearby.length} properties within {radius} km. Showing up to 10, nearest first. Small dots on the map show these properties; click a dot for details.</p>
        {nearby.length === 0 && <p>No properties in this snapshot within {radius} km. Try a wider radius or another area.</p>}
        <ul className="lease-list">{nearby.slice(0, 10).map((listing) => <li key={listing.id}>
          <a href={listing.url} target="_blank" rel="noopener noreferrer">{listing.title}<span className="small"> ↗</span></a>
          <div>{listing.price}</div>
          <div className="small muted">{listing.distance.toFixed(2)} km away · straight-line distance</div>
        </li>)}</ul>
      </>}
      <p className="small muted">Daft snapshot: 7 November 2026, 50 Cork City listings. Availability may have changed; advertised prices retain their original units. Links open Daft in a new tab.</p>
    </section>
  );
}
