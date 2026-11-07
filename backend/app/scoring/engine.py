"""Deterministic scoring engine. Owner: data/scoring.

Contract: docs/api-contract.md (POST /api/analyze). No AI in this module.

Pipeline: load the cached Cork pull (app.data.cache) -> build a ~350 m grid
-> per-cell raw signals within the config radii -> percentile-rank each into
the four sub-scores (demand/competition/access/cost) -> budget-rescaled
weighted total -> top-5 shortlist kept >= 600 m apart. Pure and
deterministic: same brief gives the same Analysis. Any failure (e.g. missing
cache) falls back to the sample analysis with data_mode="sample".
"""
from __future__ import annotations

import math

from app.config import (
    BASE_WEIGHTS,
    CELL_SIZE_M,
    CORK_BBOX,
    CORK_CENTRE,
    COST_WEIGHT_BY_BUDGET,
    CUSTOMER_FOR_COMPONENT,
    RADII,
    SHORTLIST_MIN_SPACING_M,
    SHORTLIST_SIZE,
    UNTICKED_WEIGHT,
)
from app.data.cache import Dataset, Poi, SmallArea, load
from app.data.sample import sample_analysis
from app.models import (
    Analysis,
    Brief,
    Cell,
    Competitor,
    EvidenceRow,
    Pick,
    Scores,
)

_M_PER_DEG_LAT = 111_320.0

# Evidence rows, in contract order: (metric, label).
_EVIDENCE = [
    ("residents_600m", "Residents (target ages, 600 m)"),
    ("offices_500m", "Offices (500 m)"),
    ("bus_stops_400m", "Bus stops (400 m)"),
    ("competitors_400m", "Competitors (400 m)"),
    ("distance_centre_km", "Distance from centre (km)"),
]


def analyze(brief: Brief) -> Analysis:
    try:
        return _analyze(brief, load())
    except Exception:  # noqa: BLE001 — any data failure degrades to sample
        return sample_analysis(brief)


# --- geometry + stats helpers ------------------------------------------------


def _haversine_m(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    r = 6_371_000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _pct_rank(vals: list[float]) -> list[float]:
    """Percentile rank 0-100 of each value vs the list. Ties share the mean."""
    n = len(vals)
    if n <= 1:
        return [0.0] * n
    order = sorted(range(n), key=lambda i: vals[i])
    out = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j + 1 < n and vals[order[j + 1]] == vals[order[i]]:
            j += 1
        pct = ((i + j) / 2) / (n - 1) * 100
        for k in range(i, j + 1):
            out[order[k]] = pct
        i = j + 1
    return out


def _median(vals: list[float]) -> float:
    s = sorted(vals)
    m = len(s) // 2
    return s[m] if len(s) % 2 else (s[m - 1] + s[m]) / 2


def _blend(a: list[float], b: list[float]) -> list[float]:
    return [(a[i] + b[i]) / 2 for i in range(len(a))]


def _grid() -> list[tuple[str, float, float]]:
    """(id, lng, lat) cell centres on a ~CELL_SIZE_M grid over CORK_BBOX."""
    min_lon, min_lat, max_lon, max_lat = CORK_BBOX
    mid_lat = (min_lat + max_lat) / 2
    d_lat = CELL_SIZE_M / _M_PER_DEG_LAT
    d_lon = CELL_SIZE_M / (_M_PER_DEG_LAT * math.cos(math.radians(mid_lat)))
    cells = []
    lat, row = min_lat + d_lat / 2, 0
    while lat < max_lat:
        lon, col = min_lon + d_lon / 2, 0
        while lon < max_lon:
            cells.append((f"r{row}c{col}", lon, lat))
            lon += d_lon
            col += 1
        lat += d_lat
        row += 1
    return cells


def _within(pois: list[Poi], lon: float, lat: float, radius: float) -> int:
    return sum(1 for p in pois if _haversine_m(lon, lat, p.lon, p.lat) <= radius)


def _nearest(pois: list[Poi], lon: float, lat: float, k: int) -> list[tuple[Poi, float]]:
    ranked = sorted(pois, key=lambda p: _haversine_m(lon, lat, p.lon, p.lat))
    return [(p, _haversine_m(lon, lat, p.lon, p.lat)) for p in ranked[:k]]


# --- the pipeline ------------------------------------------------------------


def _analyze(brief: Brief, data: Dataset) -> Analysis:
    by_kind: dict[str, list[Poi]] = {}
    for p in data.pois:
        by_kind.setdefault(p.kind, []).append(p)
    competitors = by_kind.get(brief.business_type, [])
    offices = by_kind.get("office", [])
    unis = by_kind.get("university", [])
    tourist = by_kind.get("tourist", [])
    shops = by_kind.get("shop", []) + by_kind.get("convenience", [])
    bus = by_kind.get("bus_stop", [])

    grid = _grid()
    n = len(grid)
    residents = [0.0] * n
    students = [0.0] * n
    office_n = [0.0] * n
    visitors = [0.0] * n
    comp_n = [0.0] * n
    bus_n = [0.0] * n
    shop_n = [0.0] * n
    dist_km = [0.0] * n
    nearest: list[list[tuple[Poi, float]]] = [[] for _ in range(n)]

    for i, (_, lon, lat) in enumerate(grid):
        for sa in data.small_areas:
            d = _haversine_m(lon, lat, sa.lon, sa.lat)
            if d <= RADII["residents"]:
                residents[i] += sa.adults()
            if d <= RADII["students_age"]:
                students[i] += sa.band("18-24")
        students[i] += _within(unis, lon, lat, RADII["students_campus"]) * 50
        office_n[i] = _within(offices, lon, lat, RADII["offices"])
        visitors[i] = _within(tourist, lon, lat, RADII["visitors_tourist"]) + _within(
            shops, lon, lat, RADII["visitors_shops"]
        )
        bus_n[i] = _within(bus, lon, lat, RADII["bus_stops"])
        shop_n[i] = _within(shops, lon, lat, RADII["access_shops"])
        comp_n[i] = _within(competitors, lon, lat, RADII["competitors"])
        nearest[i] = _nearest(competitors, lon, lat, 3)
        dist_km[i] = _haversine_m(lon, lat, *CORK_CENTRE) / 1000

    # Demand: ticked-weighted blend of four component percentiles.
    comp_pct = {
        "residents": _pct_rank(residents),
        "students": _pct_rank(students),
        "office": _pct_rank(office_n),
        "visitors": _pct_rank(visitors),
    }
    weights = {
        g: (1.0 if CUSTOMER_FOR_COMPONENT[g] in brief.customers else UNTICKED_WEIGHT)
        for g in comp_pct
    }
    wsum = sum(weights.values()) or 1.0
    demand_idx = [
        sum(comp_pct[g][i] * weights[g] for g in comp_pct) / wsum for i in range(n)
    ]

    dem_per_comp = [demand_idx[i] / (comp_n[i] + 1) for i in range(n)]
    comp_score = _blend(_pct_rank([-c for c in comp_n]), _pct_rank(dem_per_comp))
    access_score = _blend(_pct_rank(bus_n), _pct_rank(shop_n))
    cost_score = _pct_rank(dist_km)  # farther from centre = more cost advantage
    demand_score = _pct_rank(demand_idx)

    w = _budget_weights(brief.budget)
    scored = []  # (idx, Scores)
    for i in range(n):
        subs = {
            "demand": demand_score[i],
            "competition": comp_score[i],
            "access": access_score[i],
            "cost": cost_score[i],
        }
        total = sum(subs[k] * w[k] for k in subs)
        scored.append(
            Scores(
                demand=round(subs["demand"]),
                competition=round(subs["competition"]),
                access=round(subs["access"]),
                cost=round(subs["cost"]),
                total=round(total),
            )
        )

    cells = [
        Cell(id=grid[i][0], lat=grid[i][2], lng=grid[i][1], scores=scored[i])
        for i in range(n)
    ]

    medians = {
        "residents_600m": _median(residents),
        "offices_500m": _median(office_n),
        "bus_stops_400m": _median(bus_n),
        "competitors_400m": _median(comp_n),
        "distance_centre_km": round(_median(dist_km), 1),
    }
    raw = {
        "residents_600m": residents,
        "offices_500m": office_n,
        "bus_stops_400m": bus_n,
        "competitors_400m": comp_n,
        "distance_centre_km": dist_km,
    }

    order = sorted(range(n), key=lambda i: (-scored[i].total, grid[i][0]))
    shortlist = _shortlist(order, grid, scored, raw, medians, nearest)
    return Analysis(data_mode="live", brief=brief, cells=cells, shortlist=shortlist)


def _shortlist(order, grid, scored, raw, medians, nearest) -> list[Pick]:
    picks: list[Pick] = []
    chosen: list[tuple[float, float]] = []
    for i in order:
        _id, lon, lat = grid[i]
        if any(
            _haversine_m(lon, lat, clon, clat) < SHORTLIST_MIN_SPACING_M
            for clon, clat in chosen
        ):
            continue
        chosen.append((lon, lat))
        rank = len(picks) + 1
        evidence = [
            EvidenceRow(
                metric=metric,
                label=label,
                value=round(raw[metric][i], 1 if metric == "distance_centre_km" else 0),
                cork_median=medians[metric],
            )
            for metric, label in _EVIDENCE
        ]
        comps = [
            Competitor(name=p.name, distance_m=round(d))
            for p, d in nearest[i]
            if p.name
        ]
        picks.append(
            Pick(
                rank=rank,
                cell_id=_id,
                lat=lat,
                lng=lon,
                scores=scored[i],
                evidence=evidence,
                nearest_competitors=comps,
            )
        )
        if len(picks) == SHORTLIST_SIZE:
            break
    return picks


def _budget_weights(budget: str) -> dict[str, float]:
    cost = COST_WEIGHT_BY_BUDGET.get(budget, COST_WEIGHT_BY_BUDGET["moderate"])
    raw = {**BASE_WEIGHTS, "cost": cost}
    total = sum(raw.values())
    return {k: v / total for k, v in raw.items()}
