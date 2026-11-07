# SiteScout

**Before you sign a lease, see the evidence for where to sign it.**

AI-powered business location intelligence for Cork. Built at [Corkathon 2026]

## The problem

Choosing where to open a business usually rests on intuition, limited research or expensive consultancy, even though a lease is a major financial commitment. A high-visibility street can mean heavy competition, while a less obvious neighbourhood may offer stronger demand, lower costs and an underserved customer base.

SiteScout is for first-time entrepreneurs, small business owners, independent retailers, café and restaurant founders, barbers, gyms and other service businesses, and existing businesses exploring expansion.

## What it does

You give SiteScout a business type, a budget, your target customers and a city. It scores candidate locations from public data and shows a ranked, interactive map with the evidence behind every score.

**Scope for the hackathon:** Cork only, five business types:

- Specialty café
- Barber
- Gym
- Restaurant or takeaway
- Convenience store

For each of the top five picks you get:

- Four sub-scores (0-100)
- An evidence table against the Cork median (residents, offices, bus stops, competitors, distance from the centre)
- The names of the nearest competitors
- A plain-English verdict with the risks

A comparison table puts the five picks side by side.

## How it works

```
Your brief ──► Scoring engine ──► Demand      ─┐
(type, budget,  (plain code,      Competition  ├─► Challenger ──► Reporter ──► Map, shortlist,
 customers)      no AI)           Access       │   (tests the     (writes      evidence
                                  Cost        ─┘    claims)        verdicts)
                                  (run in parallel)
```

1. **Code ranks first.** The scoring engine ranks every Cork location. The ranking is deterministic: the same inputs always give the same order.
2. **Four specialist agents** (Demand, Competition, Access, Cost) read the evidence for the top five in parallel.
3. **A challenger agent** tests their claims.
4. **A reporter agent** writes the verdicts.

Each agent may only use the numbers it is given: no invented rents, footfall or prices. The evidence tables come straight from the data; the agents only explain them. The agents run on Google Gemini. If no Gemini API key is set, the app falls back to a data-only explanation.

## Scoring

Cork city and inner suburbs are cut into a grid of cells about 350 m across. Each cell gets four sub-scores from 0 to 100, ranked against every other Cork cell.

| Sub-score | Weight | What feeds it |
|---|---|---|
| Demand | 40% | Residents in the target age range within 600 m; students (universities and colleges within 1 km, 18-24 year-olds within 800 m); offices within 500 m; visitors (tourist sites within 800 m, shops within 300 m). The customer groups the user ticks set the mix |
| Competition | 25% | Fewer direct competitors within 400 m, and more demand per competitor |
| Access | 20% | Bus stops within 400 m and shops within 300 m |
| Cost advantage | 30% tight budget / 18% moderate / 8% flexible | Distance from the city centre, as a proxy for rent pressure |

Weights are rescaled so the four total 100%. The shortlist is the top five cells with at least 600 m between them, so it is not five neighbours.

## Data sources

| Source | What it gives SiteScout | Status |
|---|---|---|
| [CSO Census 2022, small areas](https://www.cso.ie) | Residents by age band per small area, with boundaries; drives the demand score | Fields checked 7 Nov 2026. Pulled by a script; first run pending |
| OpenStreetMap via the Overpass API | Competitors (cafés, hairdressers, gyms, restaurants, convenience stores), offices, universities and colleges, bus stops, shops, tourist sites | Untested from the build workspace. Community-mapped, so counts can be incomplete |
| Distance from the city centre | Stand-in for commercial rent pressure | A proxy, labelled as one in the app |
| Possible upgrades | RTB average residential rent by area (CSO tables), NTA bus timetable data | Not wired in; Cork coverage unchecked |

If the census or OpenStreetMap pull fails, the app switches to a clearly bannered **sample-data mode** so the demo still runs.

## Demo walkthrough (3 minutes)

1. Choose a specialty coffee shop, a tight budget, and students plus office workers as customers.
2. The map shades every Cork cell by score and drops five numbered pins.
3. The agent panel runs: four specialists in parallel, then the challenger, then the reporter.
4. Open pick #1: the evidence table against the Cork median, the nearest named competitors, and the challenger's risks.
5. Open the comparison table, switch the budget to flexible, and watch the ranking move.
6. Finish on the limits (below).

## Limits

SiteScout gives a better-informed starting point, **not a forecast**.

- **Cost is a proxy.** No open commercial-rent dataset for Cork was found, so cost advantage is distance from the city centre.
- **OpenStreetMap is community-mapped.** Competitor, office and shop counts can be incomplete.
- **Scores are relative.** They rank Cork locations against each other; they do not predict revenue or footfall.
- **Universities are single points.** Large campuses are under-represented in the student signal.
- **Not checked:** lease availability, planning use and local charges.
- **Agent text can still err.** The agents are told to use only the supplied numbers, but the evidence tables, drawn straight from the data, are the source of truth.

## Setup

> The application code is being written during the hackathon. This section will be filled in as the stack is chosen.

Requirements:

- A Google Gemini API key on the machine running the app, for the agent team (set it as an environment variable, e.g. `GEMINI_API_KEY`). Without it the app shows data-only explanations.
- Network access to the CSO and Overpass APIs for live data pulls; otherwise sample-data mode is used.

## Why it could be a business

- **Repeatable:** scoring is deterministic code, so results are repeatable and every number can be checked. Agents add explanation and challenge on top.
- **Versus alternatives:** manual research, expensive consultancy, or an AI chat that cannot show its data.
- **Scales by data pull, not rebuild:** census and map data are open and cover all of Ireland, so each new city is a data pull.
- **Who might pay (hypotheses to test, not findings):** first-time founders for a one-off report; enterprise supports and lenders assessing a business plan; property agents advising tenants.
- **Missing piece:** commercial rent and lease data, which is not open. A partnership with a property-data provider would make it a real business.
- **Next step:** show it to five Cork founders and ask what they would have paid to see this before signing their lease.

## Hackathon

| | |
|---|---|
| Event | Corkathon 2026, The ORB, UCC |
| Date | Saturday 7 November 2026 |
| Submission | Devpost, locks at 19:00 |
| Tracks | Best Use of Data; Best Startup Potential |
