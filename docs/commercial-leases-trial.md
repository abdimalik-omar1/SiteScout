# Commercial leases data trial

Verified 7 November 2026 against https://github.com/AnthonyBloomer/daftlistings
(package version 2.0.5). A single-page `COMMERCIAL_RENT` search for `Cork City`
initially returned residential listings: the library uses the outdated
`commercial-for-rent` API section, silently ignored upstream. The fetch script
now sends `commercial-to-rent` with the correct `pageSize` parameter directly
using the library's location payload and headers. The refreshed snapshot has 50
verified commercial rentals. Every result must have category `Commercial` and a
`/commercial-property-for-rent/` URL before the snapshot can be replaced.

Snapshot: `frontend/src/data/commercial_leases.json`. Fields: listing ID,
title, advertised price text, Daft link, latitude, longitude, commercial category,
property type and first photo URL. This is a partial
snapshot, not a complete inventory or a guarantee that properties remain available.
Prices retain their advertised units and may be “Rent Negotiable”; do not treat
them as normalized monthly rents.

Optional isolated environment, from the project root:

```sh
python3 -m venv /tmp/sitescout-daft-venv
/tmp/sitescout-daft-venv/bin/pip install daftlistings==2.0.5
cd backend
timeout 60 /tmp/sitescout-daft-venv/bin/python -m app.data.fetch_leases
```

The library does not set request timeouts, hence the external time limit.
The script refuses an empty result or invalid coordinates and replaces the cache
only after the whole result has been validated.

Click a numbered map point (1–5) or select a shortlist location to show cached listings
ordered by straight-line distance. Choose a 1, 3, or 5 km radius; the panel shows
up to ten results and brings the rentals panel into view. The snapshot is
also shown as small property dots; hover or keyboard focus displays a photo,
price and distance. Property dots have no click popup. The snapshot is
bundled with the frontend, so browsing rentals needs no live Daft requests.
Refreshing it requires rebuilding the frontend. Listings do not change the cost
proxy or analysis contract.
