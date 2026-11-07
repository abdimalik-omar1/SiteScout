# API contract

The single source of truth that lets data/scoring, agents and frontend work in parallel. The Pydantic models in `backend/app/models.py` implement it. **If you need to change a field, change it here and in `models.py` in a small PR to `main` first, and tell the others.**

Backend runs on `http://localhost:8000`. The frontend proxies `/api` to it.

## Request (both endpoints share the brief)

```json
{
  "business_type": "cafe",
  "budget": "tight",
  "customers": ["students", "office_workers"],
  "city": "Cork"
}
```

| Field | Values |
|---|---|
| `business_type` | `cafe`, `barber`, `gym`, `restaurant`, `convenience` |
| `budget` | `tight`, `moderate`, `flexible` |
| `customers` | any of `students`, `office_workers`, `residents`, `visitors` |
| `city` | `Cork` (only value for now) |

## `POST /api/analyze` — owner: data/scoring

Pure code, no AI. Deterministic: same input gives same output.

Response:

```json
{
  "data_mode": "live",
  "brief": { "...the request..." },
  "cells": [
    { "id": "c-0412", "lat": 51.8985, "lng": -8.4756,
      "scores": { "demand": 72, "competition": 55, "access": 81, "cost": 40, "total": 66 } }
  ],
  "shortlist": [
    {
      "rank": 1,
      "cell_id": "c-0412",
      "lat": 51.8985,
      "lng": -8.4756,
      "scores": { "demand": 72, "competition": 55, "access": 81, "cost": 40, "total": 66 },
      "evidence": [
        { "metric": "residents_600m", "label": "Residents (target ages, 600 m)", "value": 1840, "cork_median": 920 },
        { "metric": "offices_500m", "label": "Offices (500 m)", "value": 14, "cork_median": 3 },
        { "metric": "bus_stops_400m", "label": "Bus stops (400 m)", "value": 9, "cork_median": 4 },
        { "metric": "competitors_400m", "label": "Competitors (400 m)", "value": 2, "cork_median": 3 },
        { "metric": "distance_centre_km", "label": "Distance from centre (km)", "value": 1.2, "cork_median": 2.8 }
      ],
      "nearest_competitors": [ { "name": "Example Café", "distance_m": 180 } ]
    }
  ]
}
```

- `data_mode` is `"live"` or `"sample"`. The UI shows a banner whenever it is `"sample"`.
- `cells` is every Cork grid cell (about 350 m), used to shade the map.
- `shortlist` is the top 5 cells at least 600 m apart, rank 1 first.
- `evidence` comes straight from the data. Agents never write it.

## `POST /api/explain` — owner: agents

Body: the full `/api/analyze` response. Runs the Gemini agent team (4 specialists in parallel, then challenger, then reporter). Falls back to data-only text if `GEMINI_API_KEY` is unset.

Response:

```json
{
  "ai_mode": "gemini",
  "agent_log": [
    { "agent": "demand", "status": "done", "summary": "..." },
    { "agent": "competition", "status": "done", "summary": "..." },
    { "agent": "access", "status": "done", "summary": "..." },
    { "agent": "cost", "status": "done", "summary": "..." },
    { "agent": "challenger", "status": "done", "summary": "..." },
    { "agent": "reporter", "status": "done", "summary": "..." }
  ],
  "verdicts": [
    { "rank": 1, "verdict": "Plain-English verdict.", "risks": ["Risk one", "Risk two"] }
  ]
}
```

- `ai_mode` is `"gemini"` or `"data-only"`.
- `agent_log` drives the agent panel. `agent` is one of `demand`, `competition`, `access`, `cost`, `challenger`, `reporter`; `status` is `running`, `done` or `error`.
- `verdicts` has one entry per shortlist `rank`.
- Agents may only use numbers present in the input. No invented rents, footfall or prices.

## `GET /api/health`

Returns `{ "ok": true }`.

## Sample mode

Until the real data pull works, `/api/analyze` returns `backend/app/data/sample.py` output with `data_mode: "sample"`. This lets the frontend and agents build against realistic shapes from minute one.
