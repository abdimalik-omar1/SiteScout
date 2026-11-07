# Tasks

Back to [[Home]]. Everyone builds against [[api-contract]].

| Area | Owner | Branch | Files |
|---|---|---|---|
| Data and scoring | _assign_ | `feat/data-scoring` | `backend/app/scoring/`, `backend/app/data/` |
| Agents (Gemini) | _assign_ | `feat/agents` | `backend/app/agents/` |
| Frontend | _assign_ | `feat/frontend` | `frontend/` |

Names to assign: abdimalik, emmanuel, vini.

## Data and scoring - Vini
- [ ] CSO Census 2022 small-area pull (age bands, boundaries)
- [ ] OSM Overpass pull (competitors, offices, universities, bus stops, shops, tourist sites)
- [ ] ~350 m grid over Cork city and inner suburbs
- [ ] Four sub-scores 0-100 ranked against all Cork cells; weights per budget
- [ ] Top 5 with at least 600 m spacing; evidence table vs Cork median
- [ ] Sample-data fallback stays working (`data_mode: "sample"`)
- [ ] **15:30 gate:** live data works, or we ship sample mode with a banner

## Agents - Emmanuel
- [ ] Gemini client + `GEMINI_API_KEY` handling
- [ ] 4 specialists in parallel, then challenger, then reporter
- [ ] Prompts restrict agents to supplied numbers only
- [ ] `agent_log` events for the UI panel
- [ ] Data-only fallback when no key

## Frontend - Abdimalik
- [ ] Brief form (type, budget, customers)
- [ ] Leaflet map shaded by cell score, 5 numbered pins
- [ ] Agent panel (running/done per agent)
- [ ] Pick detail: sub-scores, evidence table, competitors, verdict, risks
- [ ] Comparison table; budget switch re-ranks
- [ ] Sample-mode banner; limits footer
