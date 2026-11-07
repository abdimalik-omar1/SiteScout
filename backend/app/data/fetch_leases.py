"""Optional data trial: install daftlistings==2.0.5, then run from backend/:

    timeout 60 python -m app.data.fetch_leases

Fetches one page only; never called by the scoring engine or API.
"""
import json
import math
from pathlib import Path

from daftlistings import Daft, SearchType


def main() -> None:
    search = Daft()
    search.set_search_type(SearchType.COMMERCIAL_RENT)
    search.set_location("Cork City")
    rows = []
    for listing in search.search(max_pages=1):
        lat, lng = float(listing.latitude), float(listing.longitude)
        if not (math.isfinite(lat) and math.isfinite(lng) and -90 <= lat <= 90 and -180 <= lng <= 180):
            raise ValueError(f"Invalid coordinates for listing {listing.id}")
        rows.append(dict(id=listing.id, title=listing.title, price=listing.price,
                         url=listing.daft_link, lat=lat, lng=lng))
    if not rows:
        raise ValueError("No listings returned; preserving existing cache")
    output = Path(__file__).resolve().parents[3] / "frontend/src/data/commercial_leases.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(".tmp")
    temporary.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    temporary.replace(output)
    print(f"Saved {len(rows)} commercial rentals to {output}")


if __name__ == "__main__":
    main()
