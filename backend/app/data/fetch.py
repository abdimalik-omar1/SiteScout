"""One-time live pull of Cork data -> disk cache (app/data/cache/).

Run once to refresh the cache; the engine then serves it offline.

    python -m app.data.fetch   (from backend/, with deps installed)

Sources:
- Boundaries + centroids: Tailte Éireann ArcGIS (CSO Small Areas 2022).
- Age bands: CSO SAPS 2022 CSV, joined on small-area GUID.
- POIs: OpenStreetMap via the Overpass API.
"""
from __future__ import annotations

import csv
import io
import json
import time
from pathlib import Path

import httpx

from app.config import CORK_BBOX
from app.data.cache import CACHE_DIR

UA = {"User-Agent": "SiteScout/0.1 (Corkathon 2026; location intelligence demo)"}

ARCGIS = (
    "https://services-eu1.arcgis.com/BuS9rtTsYEV5C0xh/arcgis/rest/services/"
    "Small_Area_National_Statistical_Boundaries_2022_Ungeneralised_view/"
    "FeatureServer/0/query"
)
SAPS_CSV = (
    "https://www.cso.ie/en/media/csoie/census/census2022/"
    "SAPS_2022_Small_Area_UR_171024.csv"
)
OVERPASS_MIRRORS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]

AGE_BANDS = [
    ("0-17", 0, 17),
    ("18-24", 18, 24),
    ("25-44", 25, 44),
    ("45-64", 45, 64),
    ("65+", 65, 200),
]


def _band_for(age: int) -> str:
    for label, lo, hi in AGE_BANDS:
        if lo <= age <= hi:
            return label
    return "65+"


def fetch_small_areas() -> list[dict]:
    ages = _fetch_saps_ages()
    min_lon, min_lat, max_lon, max_lat = CORK_BBOX
    params = {
        "where": "SA_URBAN_AREA_NAME='Cork city and suburbs'",
        "geometry": f"{min_lon},{min_lat},{max_lon},{max_lat}",
        "geometryType": "esriGeometryEnvelope",
        "inSR": "4326",
        "outSR": "4326",
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": "SA_GUID_2022,SA_PUB2022,ED_ENGLISH",
        "returnCentroid": "true",
        "returnGeometry": "false",
        "resultRecordCount": "2000",
        "f": "json",
    }
    r = httpx.get(ARCGIS, params=params, headers=UA, timeout=90)
    r.raise_for_status()
    feats = r.json().get("features", [])
    out, missing = [], 0
    for f in feats:
        a = f["attributes"]
        c = f.get("centroid")
        guid = a.get("SA_GUID_2022")
        if not c or guid not in ages:
            missing += 1
            continue
        out.append(
            {
                "id": a.get("SA_PUB2022"),
                "name": a.get("ED_ENGLISH"),
                "lon": c["x"],
                "lat": c["y"],
                "age_bands": ages[guid],
            }
        )
    print(f"small_areas: {len(out)} joined, {missing} dropped")
    return out


def _fetch_saps_ages() -> dict[str, dict[str, int]]:
    r = httpx.get(SAPS_CSV, headers=UA, timeout=120)
    r.raise_for_status()
    reader = csv.DictReader(io.StringIO(r.text))
    col_band: dict[str, str] = {}
    for col in reader.fieldnames or []:
        if not col.startswith("T1_1AGE"):
            continue
        core = col[len("T1_1AGE"):].rstrip("MF")
        if not core or core in ("T", "TT"):
            continue
        lo = core.split("_")[0]
        if not lo.isdigit():
            continue
        col_band[col] = _band_for(int(lo))
    ages: dict[str, dict[str, int]] = {}
    for row in reader:
        bands = {label: 0 for label, _, _ in AGE_BANDS}
        for col, band in col_band.items():
            v = row.get(col) or "0"
            bands[band] += int(v) if v.isdigit() else 0
        ages[row["GUID"]] = bands
    return ages


def _classify(tags: dict[str, str]) -> str | None:
    if tags.get("amenity") == "cafe":
        return "cafe"
    if tags.get("shop") in ("hairdresser", "barber"):
        return "barber"
    if tags.get("leisure") == "fitness_centre" or tags.get("amenity") == "gym":
        return "gym"
    if tags.get("amenity") in ("restaurant", "fast_food"):
        return "restaurant"
    if tags.get("shop") == "convenience":
        return "convenience"
    if tags.get("amenity") in ("university", "college"):
        return "university"
    if tags.get("highway") == "bus_stop":
        return "bus_stop"
    if tags.get("tourism") in ("attraction", "museum", "gallery", "artwork", "viewpoint", "zoo"):
        return "tourist"
    if tags.get("office"):
        return "office"
    if tags.get("shop"):
        return "shop"
    return None


def _overpass(query: str, attempts: int = 3) -> dict:
    last = None
    for i in range(attempts):
        for url in OVERPASS_MIRRORS:
            try:
                r = httpx.post(url, data={"data": query}, headers=UA, timeout=180)
                if r.status_code in (429, 502, 503, 504):
                    last = f"{url} -> {r.status_code}"
                    continue
                r.raise_for_status()
                return r.json()
            except (httpx.HTTPError, ValueError) as e:
                last = f"{url} -> {type(e).__name__}"
                continue
        time.sleep(5 * (i + 1))
    raise RuntimeError(f"all Overpass mirrors failed; last: {last}")


def fetch_pois() -> list[dict]:
    min_lon, min_lat, max_lon, max_lat = CORK_BBOX
    bbox = f"{min_lat},{min_lon},{max_lat},{max_lon}"  # Overpass: S,W,N,E
    q = f"""
    [out:json][timeout:120];
    (
      nwr["amenity"~"cafe|restaurant|fast_food|university|college|gym"]({bbox});
      nwr["shop"]({bbox});
      nwr["leisure"="fitness_centre"]({bbox});
      nwr["office"]({bbox});
      nwr["tourism"]({bbox});
      node["highway"="bus_stop"]({bbox});
    );
    out center tags;
    """
    out = []
    for el in _overpass(q).get("elements", []):
        tags = el.get("tags", {})
        kind = _classify(tags)
        if not kind:
            continue
        lon = el.get("lon") or (el.get("center") or {}).get("lon")
        lat = el.get("lat") or (el.get("center") or {}).get("lat")
        if lon is None or lat is None:
            continue
        out.append(
            {"id": f"{el['type']}/{el['id']}", "kind": kind, "lon": lon, "lat": lat, "name": tags.get("name")}
        )
    by_kind: dict[str, int] = {}
    for p in out:
        by_kind[p["kind"]] = by_kind.get(p["kind"], 0) + 1
    print(f"pois: {len(out)} total -> {by_kind}")
    return out


def main() -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    (CACHE_DIR / "small_areas.json").write_text(json.dumps(fetch_small_areas()))
    (CACHE_DIR / "pois.json").write_text(json.dumps(fetch_pois()))
    print(f"cached -> {CACHE_DIR}")


if __name__ == "__main__":
    main()
