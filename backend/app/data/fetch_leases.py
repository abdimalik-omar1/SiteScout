"""Optional data trial: install daftlistings==2.0.5, then run from backend/:

    timeout 60 python -m app.data.fetch_leases

Fetches one page only; never called by the scoring engine or API.
"""
import json
import math
from pathlib import Path
from urllib.parse import urlparse

import requests

from daftlistings import Daft, SearchType


def main() -> None:
    search = Daft()
    search.set_search_type(SearchType.COMMERCIAL_RENT)
    search.set_location("Cork City")
    # 2.0.5 uses commercial-for-rent, which the API silently treats as residential.
    payload = search._make_payload()
    payload["section"] = "commercial-to-rent"
    payload["paging"] = {"from": "0", "pageSize": "50"}
    response = requests.post(search._ENDPOINT, headers=search._headers, json=payload, timeout=30)
    response.raise_for_status()
    rows = []
    for result in response.json()["listings"]:
        listing = result["listing"]
        path = listing["seoFriendlyPath"]
        if listing.get("category") != "Commercial" or not path.startswith("/commercial-property-for-rent/"):
            raise ValueError("Non-commercial rental returned; refusing to save dataset")
        lng, lat = map(float, listing["point"]["coordinates"])
        if not (math.isfinite(lat) and math.isfinite(lng) and -90 <= lat <= 90 and -180 <= lng <= 180):
            raise ValueError(f"Invalid coordinates for listing {listing['id']}")
        images = listing.get("media", {}).get("images", [])
        image = images[0].get("size400x300") if images else None
        if image and (urlparse(image).scheme != "https" or urlparse(image).hostname != "media.daft.ie"):
            raise ValueError("Unexpected property image URL")
        rows.append(dict(id=listing["id"], title=listing["title"], price=listing["price"],
                         url="https://www.daft.ie" + path, lat=lat, lng=lng,
                         category="Commercial", property_type=listing.get("propertyType"), image=image))
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
