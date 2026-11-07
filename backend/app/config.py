"""Static configuration: Cork geography, grid, scoring weights, radii.

Constants only — no logic. Values come from readme.md §Scoring and the
api-contract.md weights.
"""

# Cork city + inner suburbs bounding box and centre (lon/lat, WGS84).
CORK_BBOX = (-8.56, 51.86, -8.40, 51.92)  # (min_lon, min_lat, max_lon, max_lat)
CORK_CENTRE = (-8.4756, 51.8985)  # (lon, lat) ~ Grand Parade

CELL_SIZE_M = 350
SHORTLIST_SIZE = 5
SHORTLIST_MIN_SPACING_M = 600

# Sub-score weights before budget rescaling. Cost is budget-dependent.
BASE_WEIGHTS = {"demand": 0.40, "competition": 0.25, "access": 0.20}
COST_WEIGHT_BY_BUDGET = {"tight": 0.30, "moderate": 0.18, "flexible": 0.08}

RADII = {
    "residents": 600,
    "students_age": 800,
    "students_campus": 1000,
    "offices": 500,
    "visitors_tourist": 800,
    "visitors_shops": 300,
    "competitors": 400,
    "bus_stops": 400,
    "access_shops": 300,
}

# Demand customer groups -> the api-contract customer value that ticks them.
CUSTOMER_FOR_COMPONENT = {
    "residents": "residents",
    "students": "students",
    "office": "office_workers",
    "visitors": "visitors",
}
UNTICKED_WEIGHT = 0.15  # unticked groups still count a little
