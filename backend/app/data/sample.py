"""Clearly fake sample data so everyone can build against the contract shape.

Owner: data/scoring. Replace with the real pipeline; keep this as the fallback.
"""
from app.models import Analysis, Brief, Cell, Competitor, EvidenceRow, Pick, Scores

CENTRE = (51.8985, -8.4756)

# (lat offset, lng offset, demand, competition, access, cost)
_PICKS = [
    (0.004, -0.010, 78, 62, 84, 55),
    (-0.006, 0.012, 70, 71, 66, 68),
    (0.010, 0.006, 64, 80, 58, 74),
    (-0.012, -0.015, 59, 77, 52, 81),
    (0.002, 0.024, 55, 83, 49, 86),
]


def _total(d: int, c: int, a: int, k: int, budget: str) -> int:
    cost_w = {"tight": 30, "moderate": 18, "flexible": 8}[budget]
    weights = (40, 25, 20, cost_w)
    s = sum(w * v for w, v in zip(weights, (d, c, a, k)))
    return round(s / sum(weights))


def sample_analysis(brief: Brief) -> Analysis:
    cells: list[Cell] = []
    shortlist: list[Pick] = []
    for i, (dlat, dlng, d, c, a, k) in enumerate(_PICKS, start=1):
        scores = Scores(
            demand=d, competition=c, access=a, cost=k,
            total=_total(d, c, a, k, brief.budget),
        )
        lat, lng = CENTRE[0] + dlat, CENTRE[1] + dlng
        cell_id = f"sample-{i}"
        cells.append(Cell(id=cell_id, lat=lat, lng=lng, scores=scores))
        shortlist.append(
            Pick(
                rank=i,
                cell_id=cell_id,
                lat=lat,
                lng=lng,
                scores=scores,
                evidence=[
                    EvidenceRow(metric="residents_600m", label="Residents (target ages, 600 m)", value=1800 - i * 200, cork_median=920),
                    EvidenceRow(metric="offices_500m", label="Offices (500 m)", value=16 - i * 2, cork_median=3),
                    EvidenceRow(metric="bus_stops_400m", label="Bus stops (400 m)", value=10 - i, cork_median=4),
                    EvidenceRow(metric="competitors_400m", label="Competitors (400 m)", value=i, cork_median=3),
                    EvidenceRow(metric="distance_centre_km", label="Distance from centre (km)", value=round(0.8 + i * 0.7, 1), cork_median=2.8),
                ],
                nearest_competitors=[
                    Competitor(name="Sample Competitor A", distance_m=150 + i * 40),
                    Competitor(name="Sample Competitor B", distance_m=320 + i * 30),
                ],
            )
        )
    shortlist.sort(key=lambda p: p.scores.total, reverse=True)
    for rank, pick in enumerate(shortlist, start=1):
        pick.rank = rank
    return Analysis(data_mode="sample", brief=brief, cells=cells, shortlist=shortlist)
